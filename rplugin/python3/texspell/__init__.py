import pynvim

from protex import parse_with_default

from .tools import auto_start
from .backend import load_backend


@pynvim.plugin
class TexSpell(object):

    def __init__(self, nvim):
        self.nvim = nvim
        self.backend = None
        self._errors = []

    def start(self):
        self.hi_src_id = self.nvim.new_highlight_source()
        self.backend = load_backend(self.nvim)

    @auto_start
    def echo(self, *msg):
        for m in msg:
            quotem = m.replace("'", "''")
            self.nvim.command("echom '{}'".format(quotem))

    @pynvim.command('TexSpellChange', nargs='1')
    @auto_start
    def texspell_change(self, args):
        self.backend = load_backend(args[0])

    @pynvim.autocmd('BufWritePost', pattern='*.tex')
    def post_write(self):
        self.make_check()

    @pynvim.autocmd('VimLeave')
    def terminate(self):
        if self.backend is not None:
            self.backend.terminate()

    @pynvim.autocmd('CursorMoved')
    def show_message(self, *args):
        pos = self.nvim.current.window.cursor
        for err in self._errors:
            if err.contains(pos):
                self.echo(err.message)
                return

    @pynvim.command('TexSpellCheck')
    def texspellcheck(self):
        self.make_check()

    @auto_start
    def make_check(self):
        filename = self.nvim.current.buffer.name
        self._errors = []
        highlighs = []
        tp = []

        c = 0
        for err in self.check_errors(filename):
            self._errors.append(err)
            highlighs.extend(self.highligh_range(err.start, err.end))
            tp.append((err.start, err.end))
            c += 1

        self.nvim.current.buffer.update_highlights(self.hi_src_id, highlighs)

    def check_errors(self, filename):
        root = parse_with_default(filename)
        source = root.render()
        pos_map = root.dump_pos_map()
        for err in self.backend.check(source):
            err.toggle_pos_mode(pos_map)
            yield err

    @auto_start
    def highligh_range(self, start, end, hi_id='TexSpellError'):
        if end <= start:
            return []
        else:
            lst = []
            if start.line < end.line:
                lst.append((hi_id, start.line, start.col, 2000))
                start.new_line()
            while start.line < end.line:
                lst.append((hi_id, start.line))
                start = start.new_line()
            lst.append((hi_id, start.line, start.col, end.col))
            return lst
