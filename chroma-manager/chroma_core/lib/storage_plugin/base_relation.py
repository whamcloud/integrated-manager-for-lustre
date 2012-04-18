#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


class BaseRelation(object):
    @property
    def key(self):
        return "%s_%s" % (self.subscribe_to, self.attributes)

    def val(self, resource):
        return tuple([getattr(resource, field_name) for field_name in self.attributes])
