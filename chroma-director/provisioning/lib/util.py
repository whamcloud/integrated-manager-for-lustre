

class LazyStruct(object):
    """
    It's kind of like a struct, and I'm lazy.
    """
    def __init__(self, **kwargs):
        self.__dict__ = kwargs

    def __getattr__(self, key):
        return self.__dict__[key]
