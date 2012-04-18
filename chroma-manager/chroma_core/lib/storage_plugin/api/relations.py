#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from chroma_core.lib.storage_plugin.base_relation import BaseRelation


class Subscribe(BaseRelation):
    def __init__(self, subscribe_to, attributes):
        self.attributes = attributes
        self.subscribe_to = subscribe_to


class Provide(BaseRelation):
    def __init__(self, provide_to, attributes):
        self.attributes = attributes
        self.provide_to = provide_to
