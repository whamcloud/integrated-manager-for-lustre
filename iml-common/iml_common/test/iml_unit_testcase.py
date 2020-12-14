# Copyright (c) 2020 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import mock
import unittest
from iml_common.lib import util


class ImlUnitTestCase(unittest.TestCase):
    def setUp(self):
        super(ImlUnitTestCase, self).setUp()

        mock.patch.object(
            util,
            "platform_info",
            util.PlatformInfo("Linux", "CentOS", 7.2, "7.21552", 2.7, 7, "3.10.0-327.36.3.el7.x86_64"),
        ).start()

        self.addCleanup(mock.patch.stopall)
