from hydra_agent.context import Context

class FileSystemMixin(object):
    """Mixin for Audit subclasses.  Classes that inherit from
    this mixin will get a number of methods for interacting with a
    filesystem.  The context property provides a way to override the
    default filesystem context ("/") for unit testing.
    """

    def __set_context(self, ctx):
        if hasattr(ctx, "root"):
            self.__context = ctx
        else:
            self.__context = Context(ctx)

    def __get_context(self):
        return self.__context

    context = property(__get_context, __set_context, doc="""
        The filesystem context (defaults to "/")""")

    def __init__(self):
        self.__set_context("/")

    def read_lines(self, filename, filter_f=None):
        """Read/strip all lines from filename and return them as a list.
        
        If the optional filter_f argument is supplied, it will be applied
        prior to stripping each line.
        """
        fh = open(self.context.abs(filename))
        try:
            return [line.rstrip("\n") for line in 
                    filter_f and filter(filter_f, fh.readlines()) or fh.readlines()]
        finally:
            fh.close()

    def read_string(self, filename):
        """Read one line from a file and return it as a string."""
        return self.read_lines(filename)[0]

    def read_int(self, filename):
        """Read one line from a file and return it as an int."""
        return int(self.read_string(filename))
