# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


class DepCache(object):
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.cache = {}

    @classmethod
    def clear(cls):
        cls.instance = None

    def _get(self, obj, state):
        if state:
            return obj.get_deps(state)
        else:
            return obj.get_deps()

    def get(self, obj, state=None):
        from chroma_core.models import StatefulObject

        if state == None and isinstance(obj, StatefulObject):
            state = obj.state

        if state:
            key = (obj, state)
        else:
            key = obj

        try:
            v = self.cache[key]
            self.hits += 1

            return v
        except KeyError:
            self.cache[key] = self._get(obj, state)
            self.misses += 1
            return self.cache[key]
