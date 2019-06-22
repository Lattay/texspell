from warnings import warn
import os

from protex.text_pos import TextPos

from .error import SpellError
from .tools import auto_start, log

from .languagetool import LanguageToolServerInterface


class Backend:
    def __init__(self, name, nvim):
        self.name = name
        self.nvim = nvim

    def error(self, msg):
        if not msg.endswith('\n'):
            msg += '\n'
        self.nvim.err_write(msg)

    def terminate(self):
        pass


class NotABackend(Backend):
    def check(self, err):
        self.error('There is no backend registered with the name {}'.format(self.name))


_backend_map = {}


def register_backend(name):
    def dec(cls):
        if name in _backend_map:
            warn('Existing {} backend have been overridden.')
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
    blines = source.encode('utf8').split(b'\n')
    bcum_length = [0 for _ in range(len(blines) + 1)]
    for i, line in enumerate([''] + blines):
        bcum_length[i] = len(line) + 1 + (bcum_length[i - 1] if i > 0 else 0)

    lines = source.split('\n')
    cum_length = [0 for line in lines]
    for i, line in enumerate([''] + lines[:-1]):
        cum_length[i] = len(line) + 1 + (cum_length[i - 1] if i > 0 else 0)

    def mkpos(offset):
        i = find_line(offset, bcum_length)
        shift = bcum_length[i]
        log('shift: {}, i: {}, offset: {}', shift, i, offset)

        cp_column = len(blines[i][:offset - shift].decode('utf8'))
        cp_offset = cum_length[i] + cp_column + 1
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
                offset = err['offset']
                length = err['context']['length']
                start = mkpos(offset + 1)
                end = mkpos(offset + length)
                yield SpellError(
                    start, end, err['message'], short=err['shortMessage'],
                    code=err['rule']['id']
                )
        except Exception as e:
            self.error('Something wrong happened: {}'.format(e))

    def terminate(self):
        if self.server is not None:
            self.server.terminate()
