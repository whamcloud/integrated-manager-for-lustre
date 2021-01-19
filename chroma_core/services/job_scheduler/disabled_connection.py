# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


class DisabledConnection(object):
    class DisabledConnectionUsed(Exception):
        def __init__(self):
            super(DisabledConnection.DisabledConnectionUsed, self).__init__(
                "Attempted to use database from a step which does not have database=True"
            )

    def __getattr__(self, item):
        raise DisabledConnection.DisabledConnectionUsed()


DISABLED_CONNECTION = DisabledConnection()
