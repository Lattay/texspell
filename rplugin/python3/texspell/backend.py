from warnings import warn
import os

from protex.text_pos import TextPos

from .error import SpellError
from .tools import auto_start

from .languagetool import LanguageToolServerInterface


class Backend:
    def __init__(self, name, nvim):
        self.name = name
        self.nvim = nvim

    def error(self, msg):
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


def mkmkpos(source):
    lines = source.split('\n')
    lines_length = [len(line) for line in lines]

    def mkpos(source, offset):
        i = 0
        shift = 0
        while offset > shift:
            shift += 1 + lines_length[i]
            i += 1
        return TextPos(offset, i, offset - shift + 1)

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
                start = mkpos(offset)
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
