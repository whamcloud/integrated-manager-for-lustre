#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2015 Intel Corporation All Rights Reserved.
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


import collections
# OrderedDict is part of the collections module in python2.7
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict


NameValueItem = collections.namedtuple("NameValueItem", ['name', 'value'])


# NameValueList provides for list of entities where each one has a name and a value
# they can then be accessed like a dictionary
#
# Create can occur using:
# a dict which contains {'name': name, 'value': value}
# a NameValueItem
# nothing which gives an empty NameValueList
class NameValueList(OrderedDict):
    def __init__(self, entries = []):
        super(NameValueList, self).__init__()

        for entry in entries:
            self.add(entry)

    def add(self, entry):
        if type(entry) == dict:
            if 'name' in entry and 'value' in entry:
                self[entry['name']] = entry['value']
            else:
                for key, value in entry.items():
                    self[key] = value
        elif type(entry) == NameValueItem:
            self[entry.name] = entry.value
        else:
            raise TypeError("%s is not understood" % entry)

    # We have to override keys because it is based on the iterator.
    def keys(self):
        return [item.name for item in self]

    # __iter__ differs because the return is an item with the name and the value
    # See collection below
    def __iter__(self):
        for key in super(NameValueList, self).__iter__():
            yield NameValueItem(key, self[key])

    # Because __iter__ doesn't return just the key we have to overload this as well.
    def iteritems(self):
        for item in self:
            yield (item.name, item.value)

    def collection(self):
        return [{'name': entry.name, 'value': entry.value} for entry in self]
