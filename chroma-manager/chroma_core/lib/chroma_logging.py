#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import settings
import logging.handlers
import os
from pwd import getpwnam


class WatchedFileHandlerWithOwner(logging.handlers.WatchedFileHandler):

    def __init__(self, *args, **kwargs):
        self._owner = kwargs.pop('owner')
        logging.handlers.WatchedFileHandler.__init__(self, *args, **kwargs)

    def _open(self):
        stream = logging.handlers.WatchedFileHandler._open(self)
        if stream and not settings.DEBUG:
            pwd = getpwnam(self._owner)
            os.chown(self.baseFilename, pwd.pw_uid, pwd.pw_gid)
        return stream
