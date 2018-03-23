# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

from copy import deepcopy
import json
import random
import errno
import os
from iml_common.lib import util

# It is my intention to create a factory class that will actually allow these to be created with a definition
# like the namedtuple. But this is a first step towards that, and if I fixup the factory class then the consumers of
# those classes will not change.
# PacemakerState = namedstruct(PacemakerState, ['state'])
# CorosyncState = namedstruct(CorosyncState, ['state', 'mcast_port])


class DictStruct(dict):
    '''
    Slightly elaborate implementation given the purpose today for just this and
the following 2 classes. But maybe it will develop into something more useful.
The key thing here is that at times out dict based structures turn back into
dict's. For example when loading from file. This class allows them to be
retured with the simple

    struct = DictStruct.from_dict(dictionary)

    you can also if you know what it is say

    known_struct = KnownStruct.from_dict(dictionary)

    Maybe we can even add some post hook to json.loads (to make this happen
automagically). I've chosen __dict_struct_type__ so that we don't get a name
clash with something.

    At present I'm not putting this in iml_common, because I'm not convinced it
is good enough yet as an idea, but maybe moving forwards with a little more
work and generalization we can do that.
    '''

    def __init__(self):
        super(DictStruct, self).__init__()
        self['__dict_struct_type__'] = self.__class__.__module__ + "." + self.__class__.__name__

    @classmethod
    def from_dict(cls, dict):
        cls_name = dict.pop('__dict_struct_type__')
        cls_ = next(class_ for class_ in util.all_subclasses(DictStruct)
                           if class_.__module__ + "." + class_.__name__ == cls_name)
        return cls_(**dict)

    @classmethod
    def convert_dict(cls, dictionary):
        for key, value in dictionary.iteritems():
            if type(value) is dict:
                cls.convert_dict(value)
                if '__dict_struct_type__' in value:
                    dictionary[key] = cls.from_dict(value)


def load_data(filename):
    return json.loads(open(os.path.join(
                               os.path.dirname(os.path.abspath(__file__)),
                               filename),
                           'r').read())


def perturb(value, max_perturb, min_bound, max_bound):
    perturbation = random.randint(0, max_perturb * 2) - max_perturb
    value += perturbation
    value = max(min_bound, value)
    value = min(max_bound, value)
    return value


class Persisted(object):
    filename = None
    default_state = {}

    def __init__(self, path):
        self.path = path

        if not self.path:
            self.reset_state()
        else:
            try:
                self.state = json.load(open(os.path.join(self.path, self.filename), 'r'))

                # Now fixup and DictStruct's in the data
                DictStruct.convert_dict(self.state)
            except IOError:
                self.reset_state()

    def save(self):
        if self.path:
            json.dump(self.state, open(os.path.join(self.path, self.filename), 'w'), indent=4)

    def delete(self):
        if not self.path:
            return

        try:
            os.unlink(os.path.join(self.path, self.filename))
        except OSError, e:
            if e.errno == errno.ENOENT:
                pass
            else:
                raise

    def reset_state(self):
        self.state = deepcopy(self.default_state)
