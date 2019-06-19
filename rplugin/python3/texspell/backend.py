from warnings import warn
from subprocess import Popen, PIPE
import json
import os
from urllib.request import Request, urlopen
from urllib.parse import urlencode, quote

from protex.text_pos import TextPos

from .error import SpellError
from .tools import auto_start


class Backend:
    def __init__(self, name, nvim):
        self.name = name
        self.nvim = nvim

    def error(self, msg):
        self.nvim.err_write(msg)


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


class SubProcessError(Exception):
    pass


class LanguageToolInterface:
    '''
    Simple but terribly slow way to use languagetool.
    '''
    def __init__(self, path, lang):
        self.path = path
        self.jar = os.path.join(self.path, 'languagetool-commandline.jar')
        self.lang = lang

    def parse(self, content):
        return json.loads(content)

    def check(self, source):
        p = Popen(['java', '-jar', self.jar, '--json', '-l', self.lang],
                  stdin=PIPE, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate(source.encode('utf8'))
        # if err:
        #     raise SubProcessError(err.decode('utf8'))
        return self.parse(out.decode('utf8'))['matches']


class LanguageToolServer(LanguageToolInterface):
    '''
    More complex but more efficient use of LanguageTool.
    '''
    def __init__(self, path, lang, port=9876):
        super().__init__(path, lang)
        self.jar = os.path.join(self.path, 'languagetool-server.jar')
        self.port = port
        self.proc = Popen([
            'java', '-cp', self.jar, 'org.languagetool.server.HTTPServer',
            '--port', str(self.port), '--allow-origin localhost', '-l', self.lang
        ])

    def request(self, content):
        data = urlencode({
            'text': content,
            'language': self.lang,
            'enabledOnly': self.enabledOnly
        }, quote_via=quote, safe=' ')
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        return Request('http://localhost:{}/v2/check', data=data, headers=headers,
                       method='POST')

    def check(self, source):
        req = self.request(source)
        resp = urlopen(req)
        body = resp.read().decode('utf')
        if resp.status // 100 >= 4:
            raise SubProcessError('Server error.' + body)
        return self.parse(body)['matches']


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
        self.ltpath = os.path.expanduser(self.nvim.eval('g:texspell_languagetool_path'))
        self.ltport = self.nvim.eval('g:texspell_languagetool_port')
        self.lang = self.nvim.eval('g:texspell_lang')
        self.server = LanguageToolServer(self.ltpath, self.lang, self.ltport)

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
