from warnings import warn
import os

from protex.text_pos import TextPos

from .error import SpellError
from .tools import auto_start, log

from .languagetool import LanguageToolServerInterface


class Backend:
    _backend_name = ''

    def __init__(self, name, nvim):
        self.name = name
        self.nvim = nvim

    def error(self, msg):
        if not msg.endswith('\n'):
            msg += '\n'
        self.nvim.err_write(msg)

    def terminate(self):
        pass

    def __repr__(self):
        return self._backend_name if self._backend_name else 'generic'

    def status(self):
        return ''


class NotABackend(Backend):
    _backend_name = 'generic'

    def check(self, err):
        self.error('There is no backend registered with the name {}'.format(self.name))

    def status(self):
        return ''


_backend_map = {}


def register_backend(name):
    def dec(cls):
        if name in _backend_map:
            warn('Existing {} backend have been overridden.')
        if cls._backend_name == '':
            cls._backend_name = name
        _backend_map[name] = cls
        return cls
    return dec


def load_backend(nvim):
    name = nvim.eval('g:texspell_engine')
    return _backend_map.get(name, NotABackend)(name, nvim)


def find_line(n, cumsum):
    '''
    Binary search in cumsum.
    '''
    if not cumsum:
        return 0
    a, b = 0, len(cumsum) - 1
    m = (a + b) // 2
    while a + 1 < b:
        if cumsum[m] == n:
            return m
        elif cumsum[m] > n:
            b = m
            m = (a + b) // 2
        else:
            a = m
            m = (a + b) // 2
    return a


def mkmkpos(source):
    '''
    Precompute data to convert a raw offset in term of bytes into a TextPos
    in term of codepoint.
    '''
    lines = source.split('\n')
    cum_length = [0 for line in lines]
    for i, line in enumerate([''] + lines[:-1]):
        cum_length[i] = len(line) + 1 + ((cum_length[i - 1]) if i > 0 else 0)

    def mkpos(offset):
        i = find_line(offset, cum_length)
        shift = cum_length[i]

        cp_column = offset - shift
        cp_offset = cum_length[i] + cp_column
        return TextPos(cp_offset, cp_column, i + 1)

    return mkpos


@register_backend('languagetool')
class LanguageTool(Backend):

    def __init__(self, name, nvim):
        self.server = None
        super().__init__(name, nvim)

    def start(self):
        self.ltpath = os.path.expanduser(self.nvim.eval('g:texspell_languagetool_path'))
        self.ltport = self.nvim.eval('g:texspell_languagetool_port')
        self.lang = self.nvim.eval('g:texspell_lang')
        self.server = LanguageToolServerInterface(self.ltpath, self.lang, self.ltport)

    @auto_start
    def check(self, source):
        mkpos = mkmkpos(source)
        try:
            for err in self.server.check(source):
                yield self.make_error(err, mkpos)
        except Exception as e:
            self.error('Something wrong happened: {}'.format(e))

    def make_error(self, err, mkpos):
        offset = err['offset']
        length = err['length']
        start = mkpos(offset + 1)
        end = mkpos(offset + length)

        error = SpellError(
            start, end, err['message'], short=err['shortMessage'],
            context=err['context']['text'],
            code=err['rule']['id'], raw=err
        )

        if err['type'].get('typeName', None) == 'UnknownWord':
            st = err['context']['offset']
            en = st + err['context']['length'] + 1
            error.message += ': ' + err['context']['text'][st:en]

        return error

    def terminate(self):
        if self.server is not None:
            self.server.terminate()

    @auto_start
    def status(self):
        return 'Using server interface from {0}, listening on port {1}.'.format(
            self.ltpath,
            self.ltport
        )
