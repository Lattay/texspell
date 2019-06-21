from functools import wraps


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
