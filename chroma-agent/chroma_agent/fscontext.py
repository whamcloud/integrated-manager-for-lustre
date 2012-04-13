import os


class FileSystemContext:
    """Filesystem abstraction which allows us to more easily unit-test
    our code."""

    def __init__(self, root="/"):
        self.root = root

    def join(self, a, b):
        path = os.path.join(a, b)
        return self.abs(path)

    def abs(self, path):
        if os.path.isabs(path):
            return os.path.join(self.root, path[1:])
        else:
            return os.path.join(self.root, path)
