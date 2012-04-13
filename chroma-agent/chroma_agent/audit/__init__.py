def local_audit_classes(fscontext=None):
    classes = []
    classes.extend(lustre.local_audit_classes(fscontext))
    classes.append(getattr(node, 'NodeAudit'))
    return classes


class BaseAudit(object):
    """Base Audit class."""
    def __init__(self, **kwargs):
        self.raw_metrics = {}

    def metrics(self):
        raise NotImplementedError

import lustre
import node
