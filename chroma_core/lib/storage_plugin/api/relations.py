# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from chroma_core.lib.storage_plugin.base_relation import BaseRelation


class Subscribe(BaseRelation):
    def __init__(self, subscribe_to, attributes, ignorecase=False):
        self.attributes = attributes
        self.subscribe_to = subscribe_to
        self.ignorecase = ignorecase

    def __repr__(self):
        return "<Subscribe %s%s>" % (self.subscribe_to.__name__, self.attributes)


class Provide(BaseRelation):
    def __init__(self, provide_to, attributes, ignorecase=False):
        self.attributes = attributes
        self.provide_to = provide_to
        self.ignorecase = ignorecase

    def __repr__(self):
        return "<Provide %s%s>" % (self.provide_to.__name__, self.attributes)
