import pynvim

from protex import parse_with_default

from .tools import auto_start
from .backend import load_backend


@pynvim.plugin
class TexSpell(object):

    def __init__(self, nvim):
        self.nvim = nvim
        self.backend = None

    def start(self):
        self.hi_src_id = self.nvim.new_highlight_source()
        self.backend = load_backend(self.nvim)

    @pynvim.command('TexSpellChange', nargs='1')
    @auto_start
    def texspell_change(self, args):
        self.backend = load_backend(args[0])

    @pynvim.autocmd('BufWritePost', pattern='*.tex')
    @auto_start
    def post_write(self):
        self.apply_texspell()

    @pynvim.autocmd('VimLeave')
    def terminate(self):
        if self.backend is not None:
            self.backend.terminate()

    @pynvim.command('TexSpellCheck')
    @auto_start
    def apply_texspell(self):
        filename = self.nvim.current.buffer.name
        self._errors = []
        highlighs = []

        c = 0
        for err in self.check_errors(filename):
            self._errors.append(err)
            highlighs.extend(self.highligh_range(err.start, err.end))
            c += 1

        self.nvim.err_write("Found {} errors.".format(c))

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
                start.newline()
            while start.line < end.line:
                lst.append((hi_id, start.line))
                start = start.newline()
            lst.append((hi_id, start.line, start.col, end.col))
            return lst
