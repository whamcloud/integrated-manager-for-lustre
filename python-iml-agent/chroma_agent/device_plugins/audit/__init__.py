# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


def local_audit_classes():
    import lustre

    classes = []
    classes.extend(lustre.local_audit_classes())
    return classes


class BaseAudit(object):
    """Base Audit class."""

    def __init__(self, **kwargs):
        self.raw_metrics = {}

    def metrics(self):
        raise NotImplementedError

    def properties(self):
        return {}
