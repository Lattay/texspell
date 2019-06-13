from functools import wraps


def auto_start(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        if not getattr(self, '_ready', False):
            self.start()
            self._ready = True
        return method(self, *args, **kwargs)
    return wrapper
