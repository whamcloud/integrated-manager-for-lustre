def local_audit_classes(fscontext=None):
    classes = []
    classes.extend(lustre.local_audit_classes(fscontext))
    classes.append(getattr(node, 'NodeAudit'))
    return classes

class BaseAudit(object):
    """Base Audit class."""
    def __init__(self, **kwargs):
        from collections import defaultdict
        self.raw_metrics = defaultdict(lambda: defaultdict())

    def metrics(self):
        raise NotImplementedError

import mixins, lustre, node, local
