#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


def chroma_settings():
    """
    Walk back up parent directories until settings.py is found.
    Insert that directory as the first entry in sys.path.
    Import the settings module, then return it to the caller.
    """
    import os
    import sys

    def _search_path(path):
        if os.path.exists(os.path.join(path, "settings.py")):
            return path
        else:
            if path == "/":
                raise RuntimeError("Can't find settings.py")
            else:
                return _search_path(os.path.dirname(path))

    site_dir = _search_path(os.path.dirname(__file__))
    sys.path.insert(0, site_dir)
    import settings
    return settings
