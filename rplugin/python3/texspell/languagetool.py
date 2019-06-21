from subprocess import Popen, PIPE
import json
import os
import random
import time
from threading import Thread
from urllib.request import Request, urlopen
from urllib.parse import urlencode, quote


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


class LanguageToolServer:
    def __init__(self, jar, port):
        self.lock_path = os.path.expanduser('~/.local/share/ltserver-{}.lock'.format(port))
        self.cmd = [
            'java', '-cp', jar, 'org.languagetool.server.HTTPServer',
            '--port', str(port), '--allow-origin localhost'
        ]
        self.stop = False

    def watchdog(self):
        key = '{}{}'.format(int(time.time() * 1000),
                            random.randint(0x10000000, 0xFFFFFFFF))

        with open(self.lock_path, 'w') as f:
            f.write(key)

        time.sleep(0.5)

        with open(self.lock_path, 'r') as f:
            res = f.read()

        if res != key:
            return  # someone override the file so it took the responsability of the server

        self.proc = Popen(self.cmd)
        while not self.stop and self.proc.returncode is None:
            time.sleep(1)
            self.proc.poll()

        if self.proc.returncode is None:
            self.proc.terminate()

        os.unlink(self.lock_path)  # release the file

    def __enter__(self):
        if not os.path.exists(self.lock_path):
            Thread(target=self.watchdog).start()
            time.sleep(3)
        return None

    def __exit__(self, *args):
        return None

    def terminate(self):
        self.stop = True


class LanguageToolServerInterface(LanguageToolInterface):
    '''
    More complex but more efficient use of LanguageTool.
    '''

    def __init__(self, path, lang, port=9876):
        super().__init__(path, lang)
        self.jar = os.path.join(self.path, 'languagetool-server.jar')
        self.port = port
        self.url = 'http://localhost:{}/v2/check'.format(self.port)
        self.server = LanguageToolServer(self.jar, self.port)
        self.enabledOnly = True

    def request(self, content):
        data = urlencode({
            'text': content,
            'language': self.lang,
            'enabledOnly': self.enabledOnly
        }, quote_via=quote, safe=' ').encode('ascii')
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        return Request(self.url, data=data, headers=headers, method='POST')

    def check(self, source):
        with self.server:
            with urlopen(self.request(source), timeout=20) as resp:
                body = resp.read().decode('utf')
                if resp.status // 100 >= 4:
                    raise SubProcessError('Server error.' + body)
        return self.parse(body)['matches']

    def terminate(self):
        self.server.terminate()
