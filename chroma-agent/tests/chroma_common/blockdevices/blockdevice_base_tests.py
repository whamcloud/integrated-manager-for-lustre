#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2016 Intel Corporation All Rights Reserved.
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


import abc
from tests.command_capture_testcase import CommandCaptureTestCase


class BaseTestBD(object):
    """
    Encapsulate BaseTestBlockDevice within class to stop test runner from running abstract base test methods
    """
    class BaseTestBlockDevice(CommandCaptureTestCase):
        """
        BlockDevice base test class with abstract test methods to ensure minimum coverage of subclasses
        """

        class_override = None
        __metaclass__ = abc.ABCMeta

        @abc.abstractmethod
        def setUp(self):
            super(BaseTestBD.BaseTestBlockDevice, self).setUp()

            self.blockdevice = None

        @abc.abstractmethod
        def test_initialize_modules(self):
            pass

        @abc.abstractmethod
        def test_filesystem_type_unoccupied(self):
            pass

        @abc.abstractmethod
        def test_filesystem_type_occupied(self):
            pass

        @abc.abstractmethod
        def test_uuid(self):
            pass

        @abc.abstractmethod
        def test_preferred_fstype(self):
            pass

        @abc.abstractmethod
        def test_device_type(self):
            pass

        @abc.abstractmethod
        def test_device_path(self):
            pass

        @abc.abstractmethod
        def test_mgs_targets(self):
            pass

        @abc.abstractmethod
        def test_targets(self):
            pass

        @abc.abstractmethod
        def test_property_values(self):
            pass

        def test_import_success_non_pacemaker(self):
            self.assertIsNone(self.blockdevice.import_(False))

        def test_import_success_with_pacemaker(self):
            self.assertIsNone(self.blockdevice.import_(False))

        def test_import_existing_non_pacemaker(self):
            self.assertIsNone(self.blockdevice.import_(False))

        def test_import_existing_with_pacemaker(self):
            self.assertIsNone(self.blockdevice.import_(False))

        def test_export_success(self):
            self.assertIsNone(self.blockdevice.export())

        def test_export_missing(self):
            self.assertIsNone(self.blockdevice.export())
