#
# INTEL CONFIDENTIAL
#
# Copyright 2013 Intel Corporation All Rights Reserved.
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

    def _load_default(self):
        self.state = deepcopy(self.default_state)

    def __init__(self, path):
        self.path = path

        if not self.path:
            self._load_default()
        else:
            try:
                self.state = json.load(open(os.path.join(self.path, self.filename), 'r'))
            except IOError:
                self._load_default()

    def save(self):
        if self.path:
            json.dump(self.state, open(os.path.join(self.path, self.filename), 'w'), indent = 4)

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
