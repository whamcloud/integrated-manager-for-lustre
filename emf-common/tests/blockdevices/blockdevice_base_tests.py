# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import abc
from emf_common.test.command_capture_testcase import CommandCaptureTestCase


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
        def test_check_module(self):
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
            self.assertIsNone(self.blockdevice.import_(True))

        def test_import_existing_non_pacemaker(self):
            self.assertIsNone(self.blockdevice.import_(False))

        def test_import_existing_with_pacemaker(self):
            self.assertIsNone(self.blockdevice.import_(True))

        def test_export_success(self):
            self.assertIsNone(self.blockdevice.export())

        def test_export_missing(self):
            self.assertIsNone(self.blockdevice.export())
