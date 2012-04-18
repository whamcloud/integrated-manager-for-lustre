#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


class AlertCondition(object):
    def __init__(self):
        self._name = None

    def set_name(self, name):
        self._name = name

    def alert_classes(self):
        raise NotImplementedError()
