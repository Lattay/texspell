import pynvim

from protex import parse_with_default

from .tool import auto_start
from .backend import load_backend
# from protex.text_pos import TextPos


def tp_to_vim_range(start, end):
    if end <= start:
        return []
    else:
        lst = []
        if start.line < end.line:
            lst.append([start.line, start.col, 2000])
            start.newline()
        while start.line < end.line:
            lst.append([start.line])
            start = start.newline()
        lst.append(start.line, start.col, end.col)
        return lst


@pynvim.plugin
class TexSpell(object):

    def __init__(self, nvim):
        self.nvim = nvim
        self.backend = None

    def start(self):
        self.backend = load_backend(self.nvim.eval('g:texspell_engine'), self.nvim)

    @auto_start
    @pynvim.command('TexSpellChange', nargs='1')
    def texspell_change(self, args):
        self.backend = load_backend(args[0])

    @auto_start
    @pynvim.autocmd('BufWritePost', pattern='*.tex', eval='expand("<afile>:p")')
    def apply_texspell(self, filename):
        self._errors = []
        for err in self.check_errors(filename):
            self._errors.append(err)
            self.highligh_range(err.start, err.end)

    def check_errors(self, filename):
        root = parse_with_default(filename)
        source = root.render()
        pos_map = root.dump_pos_map()
        for err in self.backend.check(source):
            err.toggle_pos_mode(pos_map)
            yield err

    def highligh_range(self, hi_id, start, end):
        pos = tp_to_vim_range(start, end)

        # only 8 positions can be set at once
        for i in range(0, len(pos), 8):
            self.nvim.async_call('matchaddpos', hi_id, pos[i:i + 8])
