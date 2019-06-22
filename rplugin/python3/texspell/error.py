class SpellError:
    def __init__(self, start, end, msg, source_side=False, short='', filename='anonym', code='err'):
        self.start = start
        self.end = end
        self.message = msg
        self.short = short
        self.code = code
        self.filename = filename
        self._alt_file = 'anonym'
        self.source_side = source_side

    def contains(self, c, ln):
        return (self.start.line <= ln and (self.start.col <= c or self.start.line < ln)
                and self.end.line >= ln and (self.end.col >= c or self.end.line < ln))

    def __str__(self):
        return '<SpellError: ' + self.message + '>'

    def toggle_pos_mode(self, pos_map):
        if self.source_side:
            self.start, self.end = \
                pos_map.src_to_dest_range(self.filename, self.start, self.end)
            self.filename = self._alt_file
        else:
            self._alt_file = self.filename
            self.filename, self.start, self.end = \
                pos_map.dest_to_src_range(self.start, self.end)

        self.source_side = not self.source_side
        return self.source_side
