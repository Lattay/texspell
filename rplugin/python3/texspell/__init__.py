import pynvim
from operator import attrgetter
from bisect import bisect

from protex import parse_with_default
from protex.text_pos import TextPos

from .tools import auto_start, switchable, log
from .backend import load_backend


@pynvim.plugin
class TexSpell(object):
    '''
    Definition of the TexSpell Neovim plugin.
    See README.md for more informations.
    '''

    @pynvim.command('TexSpellEnable')
    @auto_start
    def texspell_restart(self):
        '''
        Enable the plugin.
        '''
        self.enable = True
        self.backend = load_backend(self.nvim)
        list(self.backend.check(''))

    @pynvim.command('TexSpellDisable')
    def texspell_stop(self):
        '''
        Disable the plugin and stop the backend.
        '''
        self.enable = False
        self.terminate()

    @pynvim.command('TexSpellStart')
    @switchable
    @auto_start
    def texspell_start(self):
        '''
        Force everything to start and be ready.
        '''
        list(self.backend.check(''))

    @pynvim.command('TexSpellCheck')
    @switchable
    def texspellcheck(self):
        self.make_check()

    @pynvim.command('TexSpellJumpNext')
    @switchable
    def jump_next(self):
        self.jump_to(1)

    @pynvim.command('TexSpellJumpPrev')
    @switchable
    def jump_prev(self):
        self.jump_to(-1)

    @pynvim.command('TexSpellMessage')
    @switchable
    def show_message(self):
        self.update_pos()
        for err in self._errors:
            if err.start <= self.pos <= err.end:
                self.echo(err.message)
                return
        self.echo('')

    @pynvim.autocmd('BufWritePost', pattern='*.tex')
    @switchable
    def post_write(self):
        self.lines = {}

    @pynvim.autocmd('VimLeave', pattern='*.tex')
    @switchable
    def terminate(self):
        if self.backend is not None:
            self.backend.terminate()
            self.backend = None

    def __init__(self, nvim):
        self.nvim = nvim
        self.backend = None
        self._errors = []
        self._positions = []
        self.lines = {}

        self.pos = TextPos(-1, 0, 0)
        self.enable = True

    def start(self):
        self.hi_src_id = self.nvim.new_highlight_source()
        self.backend = load_backend(self.nvim)
        self.enabled = bool(self.nvim.eval('get(g:, "texspell_disable", 0) || get(b:, "texspell_disable", 0)'))

    def update_pos(self):
        row, col = self.nvim.current.window.cursor
        self.pos = TextPos(-1, col + (0 if row == 1 else 1), row)

    def clear_errors(self):
        self._errors.clear()

    def get_surround_errors(self, pos):
        if not self._errors:
            return None, None
        if pos <= self._positions[0] or pos >= self._positions[-1]:
            return self._positions[-1], self._positions[0]

        m = bisect(self._positions, pos)
        if pos == self._positions[m - 1]:
            return self._positions[(m - 2) % len(self._positions)], self._positions[m]
        return self._positions[m - 1], self._positions[m]

    @auto_start
    def jump_to(self, direct):
        self.update_pos()
        prev, next_ = self.get_surround_errors(self.pos)
        pos = None

        if direct == 1 and next_ is not None:
            pos = next_
        elif direct == -1 and prev is not None:
            pos = prev

        if pos is not None:
            self.nvim.current.window.cursor = (
                pos.line, pos.col - (0 if pos.line == 1 else 1)
            )

    @auto_start
    def echo(self, *msg):
        for m in msg:
            quotem = m.replace("'", "''")
            self.nvim.command("echom '{}'".format(quotem))

    @auto_start
    def make_check(self):
        filename = self.nvim.current.buffer.name
        self.clear_errors()

        self.highlights = []

        c = 0
        for err in self.check_errors(filename):
            self._errors.append(err)
            self.highligh_error(err)
            c += 1

        self._errors.sort(key=attrgetter('start'))
        self._positions = [err.start for err in self._errors]

        self.nvim.current.buffer.update_highlights(self.hi_src_id, self.highlights)

    def check_errors(self, filename):
        root = parse_with_default(filename)
        source = root.render()
        pos_map = root.dump_pos_map()
        for err in self.backend.check(source):
            log('Before: {} {}', err.message, err.start)
            err.toggle_pos_mode(pos_map)
            log('After: {} {}', err.message, err.start)
            err.start.col = self.get_true_column(err.start.line, err.start.col)
            err.end.col = self.get_true_column(err.end.line, err.end.col)
            log('Finally: {} {}', err.message, err.start)
            yield err

    @auto_start
    def highligh_range(self, start, end, hi_id='TexSpellError'):
        if end <= start:
            return []
        else:
            lst = []
            if start.line < end.line:
                yield (hi_id, start.line - 1,
                       start.col - (0 if start.line == 1 else 1), -1)
                start = start.new_line()
            while start.line < end.line:
                yield (hi_id, start.line - 1, 0, -1)
                start = start.new_line()
            yield (hi_id, start.line - 1,
                   start.col - (0 if start.line == 1 else 1),
                   end.col + (1 if start.line == 1 else 0))
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
