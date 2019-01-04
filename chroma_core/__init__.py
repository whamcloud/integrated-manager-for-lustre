# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import os


# Only enable long polling if we are running in a real django environment this means that in test
# environments long polling is not enabled.
try:
    settings_module = os.environ["DJANGO_SETTINGS_MODULE"]

    if not settings_module:  # If it's set but is an empty string.
        raise KeyError

except KeyError:
    pass
