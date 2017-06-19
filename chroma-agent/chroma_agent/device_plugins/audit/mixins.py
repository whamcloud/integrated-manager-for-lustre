# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import os


class FileSystemMixin(object):
    """Mixin for Audit subclasses.  Classes that inherit from
    this mixin will get some convenience methods for interacting with a
    filesystem.  The fscontext property provides a way to override the
    default filesystem context ("/") for unit testing.
    """
    # Unit tests should patch this attribute when using fixture data.
    fscontext = "/"

    def abs(self, path):
        if os.path.isabs(path):
            return os.path.join(self.fscontext, path[1:])
        else:
            return os.path.join(self.fscontext, path)

    def read_lines(self, filename, filter_f=None):
        """Return a generator for stripped lines read from the file.

        If the optional filter_f argument is supplied, it will be applied
        prior to stripping each line.
        """

        # I really don't like this, but at present I can't see a way of the Audit's knowing enough about the
        # devices to point to the correct device - The notion that Audit, Corosync, etc can all be seperate means
        # they don't have the knowledge to deal with things like zfs verse's ldiskfs. So for know if the file doesn't
        # exist and the path contains osd-ldiskfs then swap it for osd-zfs and use that - and if that doesn't exist we
        # are no worse off.
        # If I had a better solution without a major rewrite I would use it!

        filename = self.abs(filename)

        if (not os.path.isfile(filename)):
            filename = filename.replace("osd-ldiskfs", "osd-zfs")

        for line in open(filename):
            if filter_f:
                if filter_f(line):
                    yield line.rstrip("\n")
            else:
                yield line.rstrip("\n")

    def read_string(self, filename):
        """Read the first line from a file and return it as a string."""
        try:
            return self.read_lines(filename).next()
        except StopIteration:
            raise RuntimeError("read_string() on empty file: %s" % filename)

    def read_int(self, filename):
        """Read one line from a file and return it as an int."""
        return int(self.read_string(filename))

    def walk(self, path):
        """Walk the supplied path. This wrapper enables simpler unit tests."""
        return os.walk(self.abs(path))
