#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


class AlertCondition(object):
    def __init__(self, *args, **kwargs):
        self._id = kwargs.pop('id', None)

    def id(self):
        raise NotImplementedError()
