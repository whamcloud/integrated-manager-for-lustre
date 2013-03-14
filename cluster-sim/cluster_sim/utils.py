#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from copy import deepcopy
import json
import random
import errno
import os


def load_data(filename):
    return json.loads(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), filename), 'r').read())


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

        try:
            self.state = json.load(open(os.path.join(self.path, self.filename), 'r'))
        except IOError:
            self.state = deepcopy(self.default_state)

    def save(self):
        json.dump(self.state, open(os.path.join(self.path, self.filename), 'w'), indent = 4)

    def delete(self):
        try:
            os.unlink(self.filename)
        except OSError, e:
            if e.errno == errno.ENOENT:
                pass
            else:
                raise
