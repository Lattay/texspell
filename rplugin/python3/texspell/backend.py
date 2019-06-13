from warnings import warn
from string import StringIO
from subprocess import Popen
import json
import os

from protex.text_pos import text_origin, TextPos

from .error import SpellError
from .tool import auto_start


class Backend:
    def __init__(self, name):
        self.name = name

    def error(self, msg):
        return SpellError(text_origin, text_origin + 1, msg, short='config error')


class NotABackend(Backend):
    def check(self, err):
        yield self.error('There is no backend registered with the name {}'.format(self.name))


_backend_map = {}


def register_backend(name):
    def dec(cls):
        if name in _backend_map:
            warn('Existing {} backend have been overridden.')
        _backend_map[name]
        return cls
    return dec


def load_backend(name, nvim):
    return _backend_map.get(name, NotABackend)(name, nvim)


class LanguageToolInterface:
    def __init__(self, path, lang):
        self.path = path
        self.jar = os.path.join(self.path, 'languagetool-commandline.jar')
        self.lang = lang

    def parse(self, content):
        return json.loads(content)

    def check(self, source):
        with Popen(['java', '-jar', self.jar, '-l', self.lang],
                   stdin=StringIO(source), capture_output=True) as p:
            res = p.stdout.read()
        return self.parse(res)['matches']


class LanguageToolServer(LanguageToolInterface):
    def __init__(self, path, lang):
        super().__init__(path, lang)
        self.jar = os.path.join(self.path, 'languagetool-server.jar')
        self.port = 8888
        self.cmd = 'java -cp {} org.languagetool.server.HTTPServer --port {} --allow-origin \'*\''
        self.proc = Popen(['java', '-jar', path, '-l', lang])

    def check(self, source):
        errors = []
        return errors


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
    def start(self):
        self.ltpath = self.nvim.eval('g:texspell_languagetool_path')
        self.lang = self.nvim.eval('g:texspell_languagetool_lang')
        self.server = LanguageToolInterface(self.ltpath, self.server)

    @auto_start
    def check(self, source):
        mkpos = mkmkpos(source)
        for err in self.server.check(source):
            offset = err['offset']
            length = err['context']['length']
            start = mkpos(offset)
            end = mkpos(offset + length)
            yield SpellError(
                start, end, err['message'], short=err['shortMessage'],
                code=err['rule']['id']
            )
