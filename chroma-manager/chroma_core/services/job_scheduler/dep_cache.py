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

    def get(self, obj, state = None):
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
