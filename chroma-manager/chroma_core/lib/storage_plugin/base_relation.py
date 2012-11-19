#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


class BaseRelation(object):
    @property
    def key(self):
        return "%s_%s" % (self.subscribe_to, self.attributes)

    def val(self, resource):
        values = (getattr(resource, field_name) for field_name in self.attributes)
        if self.ignorecase:
            return tuple(value.lower() if isinstance(value, basestring) else value for value in values)
        return tuple(values)
