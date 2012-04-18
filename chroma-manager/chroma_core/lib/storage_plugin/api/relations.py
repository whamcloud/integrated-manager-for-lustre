#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from chroma_core.lib.storage_plugin.base_relation import BaseRelation


class Subscribe(BaseRelation):
    def __init__(self, subscribe_to, attributes):
        self.attributes = attributes
        self.subscribe_to = subscribe_to

    def __repr__(self):
        return "<Subscribe %s%s>" % (self.subscribe_to.__name__, self.attributes)


class Provide(BaseRelation):
    def __init__(self, provide_to, attributes):
        self.attributes = attributes
        self.provide_to = provide_to

    def __repr__(self):
        return "<Provide %s%s>" % (self.provide_to.__name__, self.attributes)
