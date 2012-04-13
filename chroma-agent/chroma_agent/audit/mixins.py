from chroma_agent.fscontext import FileSystemContext


class FileSystemMixin(object):
    """Mixin for Audit subclasses.  Classes that inherit from
    this mixin will get a number of methods for interacting with a
    filesystem.  The context property provides a way to override the
    default filesystem context ("/") for unit testing.
    """

    def __set_fscontext(self, ctx):
        if hasattr(ctx, "root"):
            self.__fscontext = ctx
        else:
            self.__fscontext = FileSystemContext(ctx)

    def __get_fscontext(self):
        # This bit of hackery is necessary due to the fact that mixins
        # can't have an __init__() to set things up.
        if not '_FileSystemMixin__fscontext' in self.__dict__:
            self.__fscontext = FileSystemContext()
        return self.__fscontext

    fscontext = property(__get_fscontext, __set_fscontext, doc="""
        The filesystem context (defaults to "/")""")

    def read_lines(self, filename, filter_f=None):
        """Read/strip all lines from filename and return them as a list.

        If the optional filter_f argument is supplied, it will be applied
        prior to stripping each line.
        """
        fh = open(self.fscontext.abs(filename))
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
