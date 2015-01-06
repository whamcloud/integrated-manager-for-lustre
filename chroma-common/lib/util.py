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


# This file contains utility routines that can be used from all packages.
# for example from chroma_agent.
# import chroma_agent.chroma-common.lib.utils
#
# from chroma_core
# import chroma_core.chroma-common.lib.utils

import time
from collections import MutableSequence, namedtuple

ExpiringValue = namedtuple('ExpiringValue', ['value', 'expiry'])


class ExpiringList(MutableSequence):
    """Special implementation of a python list which
     invalidate its elements after a specified 'grace_period'
    """

    def __init__(self, grace_period):
        self._container = list()
        self.grace_period = grace_period

    def __len__(self):
        return len([x for x in self])

    def __delitem__(self, index):
        del self._container[index]

    def __setitem__(self, index, value):
        self.insert(index, value)

    def __str__(self):
        return str([x for x in self])

    def __getitem__(self, index):
        cur_time = time.time()
        if cur_time > self._container[index].expiry:
            self._container = [x for x in self._container if x.expiry >= cur_time]
        return self._container[index].value

    def insert(self, index, value):
        self._container.insert(index, ExpiringValue(value, time.time() + self.grace_period))
