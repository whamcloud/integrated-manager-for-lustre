# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


class AlertCondition(object):
    def __init__(self, *args, **kwargs):
        self._id = kwargs.pop("id", None)

    def id(self):
        raise NotImplementedError()
