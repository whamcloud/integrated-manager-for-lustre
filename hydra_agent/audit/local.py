import re
import hydra_agent.audit
from hydra_agent.audit import BaseAudit
from hydra_agent.audit.mixins import FileSystemMixin

class LocalAudit(BaseAudit, FileSystemMixin):
    def __init__(self):
        # Multiple inheritance is fun!
        BaseAudit.__init__(self)
        FileSystemMixin.__init__(self)

    # FIXME: This probably ought to be a memoized property, but I'm lazy.
    def audit_classes(self):
        if not hasattr(self, 'audit_classes_list'):
            self.audit_classes_list = hydra_agent.audit.local_audit_classes(self.context)
        return self.audit_classes_list

    # Flagrantly "borrowed" from:
    # http://stackoverflow.com/questions/5575124/python-combine-several-nested-lists-into-a-dictionary
    def __mergedicts(self, *dicts):
        """Recursively merge an arbitrary number of dictionaries.
        >>> import pprint
        >>> d1 = {'a': {'b': {'x': '1',
        ...                   'y': '2'}}}
        >>> d2 = {'a': {'c': {'gg': {'m': '3'},
        ...                   'xx': '4'}}}
        >>> pprint.pprint(mergedicts(d1, d2), width=2)
        {'a': {'b': {'x': '1',
                     'y': '2'},
               'c': {'gg': {'m': '3'},
                     'xx': '4'}}}
        """
    
        keys = set(k for d in dicts for k in d)
    
        def vals(key):
            """Returns all values for `key` in all `dicts`."""
            withkey = (d for d in dicts if d.has_key(key))
            return [d[key] for d in withkey]
    
        def recurse(*values):
            """Recurse if the values are dictionaries."""
            if isinstance(values[0], dict):
                return self.__mergedicts(*values)
            if len(values) == 1:
                return values[0]
            raise TypeError("Multiple non-dictionary values for a key.")
    
        return dict((key, recurse(*vals(key))) for key in keys)

    def metrics(self):
        """Returns an aggregated dict of all subclass metrics."""
        agg_raw = {}
        for cls in self.audit_classes():
            audit = cls()
            audit.context = self.context
            audit_metrics = audit.metrics()
            agg_raw = self.__mergedicts(agg_raw, audit_metrics['raw'])

        return {'raw': agg_raw}
