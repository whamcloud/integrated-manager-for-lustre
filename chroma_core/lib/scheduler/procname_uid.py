# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


"""
Shell-based scheduler which records process name and user id.
"""

FIELDS = "name", "user"


def fetch(ids):
    "Generate process names and user ids."
    for id in ids:
        yield dict(zip(FIELDS, id.rsplit(".", 1)))
