import pynvim

from protex import parse_with_default
from protex.text_pos import TextPos

from .tools import auto_start, log
from .backend import load_backend


@pynvim.plugin
class TexSpell(object):

    def __init__(self, nvim):
        self.nvim = nvim
        self.backend = None
        self._errors = []
        self.lines = {}

        self.pos = TextPos(-1, 0, 0)

    def start(self):
        self.hi_src_id = self.nvim.new_highlight_source()
        self.backend = load_backend(self.nvim)

    def clear_errors(self):
        self._errors.clear()

    def insert_error(self, err):
        a, b, m = 0, len(self._errors) - 1, 0
        while a + 1 < b:
            m = (a + b) // 2
            if self._errors[m].start > err.start:
                b = m
            elif self._errors[m].start < err.start:
                a = m
            else:
                a = b = m
        self._errors.insert(m, err)

    def get_surround_errors(self, pos):
        a, b, m = 0, len(self._err) - 1, 0
        while a + 1 < b:
            m = (a + b) // 2
            if self._err[m].start > pos:
                b = m
            elif self._err[m].start < pos:
                a = m
            else:
                a = max(0, m - 1)
                b = min(len(self._err), m + 1)
        return self._err[a], self._err[b]

    @auto_start
    def echo(self, *msg):
        for m in msg:
            quotem = m.replace("'", "''")
            self.nvim.command("echom '{}'".format(quotem))

    @pynvim.command('TexSpellJumpNext', nargs='0')
    def jump_next(self):
        self.jump_to(1)

    @pynvim.command('TexSpellJumpPrev', nargs='0')
    def jump_prev(self):
        self.jump_to(-1)

    def jump_to(self, direct):
        prev, next = self.get_surround_errors(self.pos)

    @pynvim.command('TexSpellChange', nargs='1')
    @auto_start
    def texspell_change(self, args):
        self.backend = load_backend(args[0])

    @pynvim.autocmd('BufWritePost', pattern='*.tex')
    def post_write(self):
        self.lines = {}
        self.make_check()

    @pynvim.autocmd('VimLeave', pattern='*.tex')
    def terminate(self):
        if self.backend is not None:
            self.backend.terminate()

    @pynvim.autocmd('CursorMoved', pattern='*.tex')
    def show_message(self):
        row, col = self.nvim.current.window.cursor
        self.pos = TextPos(-1, col + 1, row - 1)
        for err in self._errors:
            if err.start <= self.pos <= err.end:
                self.echo(err.message)
                return
        self.echo('')

    @pynvim.command('TexSpellCheck')
    def texspellcheck(self):
        self.make_check()

    @auto_start
    def make_check(self):
        filename = self.nvim.current.buffer.name
        self.clear_errors()

        self.highlights = []

        c = 0
        for err in self.check_errors(filename):
            self.insert_error(err)
            self.highligh_error(err)
            c += 1

        self.nvim.current.buffer.update_highlights(self.hi_src_id, self.highlights)

    def check_errors(self, filename):
        root = parse_with_default(filename)
        source = root.render()
        log(source)
        pos_map = root.dump_pos_map()
        for err in self.backend.check(source):
            err.toggle_pos_mode(pos_map)
            err.start.col = self.get_true_column(err.start.line, err.start.col)
            err.end.col = self.get_true_column(err.end.line, err.end.col)
            yield err

    @auto_start
    def highligh_range(self, start, end, hi_id='TexSpellError'):
        if end <= start:
            return []
        else:
            lst = []
            if start.line < end.line:
                yield (hi_id, start.line - 1, start.col - 1, -1)
                start = start.new_line()
            while start.line < end.line:
                yield (hi_id, start.line - 1, 0, -1)
                start = start.new_line()
            yield (hi_id, start.line - 1, start.col - 1, end.col)
            return lst

    def get_true_column(self, ln, col):
        if ln not in self.lines:
            self.lines[ln] = self.nvim.current.buffer[ln - 1]
        line = self.lines[ln]
        return col + len(line[:col].encode('utf8')) - len(line[:col])

    @auto_start
    def highligh_error(self, err):
        for id, ln, start, end in self.highligh_range(err.start, err.end):
            self.highlights.append((id, ln, start, end))
