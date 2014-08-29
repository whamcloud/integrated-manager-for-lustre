#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2014 Intel Corporation All Rights Reserved.
#
# The source code contained or described herein and all documents related
# to the source code ("Material") are owned by Intel Corporation or its
# suppliers or licensors. Title to the Material remains with Intel Corporation
# or its suppliers and licensors. The Material contains trade secrets and
# proprietary and confidential information of Intel or its suppliers and
# licensors. The Material is protected by worldwide copyright and trade secret
# laws and treaty provisions. No part of the Material may be used, copied,
# reproduced, modified, published, uploaded, posted, transmitted, distributed,
# or disclosed in any way without Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellectual
# property right is granted to or conferred upon you by disclosure or delivery
# of the Materials, either expressly, by implication, inducement, estoppel or
# otherwise. Any license under such intellectual property rights must be
# express and approved by Intel in writing.


import chroma_agent.device_plugins.audit
from chroma_agent.device_plugins.audit import BaseAudit
from chroma_agent.device_plugins.audit.mixins import FileSystemMixin


class LocalAudit(BaseAudit, FileSystemMixin):
    def __init__(self, **kwargs):
        super(LocalAudit, self).__init__(**kwargs)

    # FIXME: This probably ought to be a memoized property, but I'm lazy.
    def audit_classes(self):
        if not hasattr(self, 'audit_classes_list'):
            self.audit_classes_list = chroma_agent.device_plugins.audit.local_audit_classes()
        return self.audit_classes_list

    # Flagrantly "borrowed" from:
    # http://stackoverflow.com/questions/5575124/python-combine-several-nested-lists-into-a-dictionary
    def __mergedicts(self, *dicts):
        """Recursively merge an arbitrary number of dictionaries.
        pyflakes:ignore >>> import pprint
        >>> d1 = {'a': {'b': {'x': '1',
        ...                   'y': '2'}}}
        >>> d2 = {'a': {'c': {'gg': {'m': '3'},
        ...                   'xx': '4'}}}
        pyflakes:ignore >>> pprint.pprint(mergedicts(d1, d2), width=2)
        {'a': {'b': {'x': '1',
                     'y': '2'},
               'c': {'gg': {'m': '3'},
                     'xx': '4'}}}
        """

        keys = set(k for d in dicts for k in d)

        def vals(key):
            """Returns all values for `key` in all `dicts`."""
            return [d[key] for d in dicts if key in d]

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
            audit_metrics = audit.metrics()
            agg_raw = self.__mergedicts(agg_raw, audit_metrics['raw'])

        return {'raw': agg_raw}

    def properties(self):
        """Returns merged properties suitable for host validation."""
        return dict(item for cls in self.audit_classes() for item in cls().properties().items())
