from hydra_agent.context import Context

def local_audit_classes(context=Context()):
    classes = []
    classes.extend(lustre.local_audit_classes(context))
    classes.append(getattr(node, 'NodeAudit'))
    return classes

class BaseAudit(object):
    """Base Audit class."""
    def __init__(self):
        from collections import defaultdict
        self.raw_metrics = defaultdict(lambda: defaultdict())

    def metrics(self):
        raise NotImplementedError

import mixins, lustre, node, local
