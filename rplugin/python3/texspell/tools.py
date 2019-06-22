from functools import wraps
from random import choices


def sign():
    return ''.join(choices('#o.', k=5))


_first_log = True


def log(s, *args):
    global _first_log
    flag = 'a'
    if _first_log:
        _first_log = False
        flag = 'w'
    with open('./texspell.log', flag) as f:
        if args:
            msg = s.format(*args)
        else:
            msg = s
        f.write('[INFO-{0}]\n{1}\n[{0}]\n'.format(sign(), msg))


def auto_start(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        if not getattr(self, '_ready', False):
            abort = self.start()
            if abort:
                return None
            self._ready = True
        return method(self, *args, **kwargs)
    return wrapper
