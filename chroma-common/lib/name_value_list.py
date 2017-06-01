# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


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
