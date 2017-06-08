# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import mock

from django.utils import unittest


class ImlUnitTestCase(unittest.TestCase):
    def setUp(self):
        self.addCleanup(mock.patch.stopall)
