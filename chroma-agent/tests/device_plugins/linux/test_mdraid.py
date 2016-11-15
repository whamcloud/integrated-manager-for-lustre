import json
import os

import mock
from chroma_agent.device_plugins.linux import MdRaid
from tests.device_plugins.linux.test_linux import LinuxAgentTests, MockDmsetupTable


class TestMDRaid(LinuxAgentTests):

    def setUp(self):
        super(TestMDRaid, self).setUp()

        self.md_value_good = {'mdstat': """Personalities : [raid1]
md127 : active (auto-read-only) raid1 sdc[1] sdb[0]
      16056704 blocks super 1.2 [2/2] [UU]

md128 : active (auto-read-only) raid0 sdd[0]
      16056704 blocks super 1.2 [2/2] [UU]

unused devices: <none>\n""",
                              'mdadm': {"/dev/md/md-name-test:1": """ARRAY /dev/md/md-name-test:1 level=raid0 num-devices=1 metadata=1.2 name=mac-node:1 UUID=15054135:be3426c6:f1387822:49830fb6
   devices=/dev/sdd\n""",
                                        "/dev/md/md-name-test:123": """ARRAY /dev/md/md-name-test:123 level=raid1 num-devices=2 metadata=1.2 name=mac-node:1 UUID=15054135:be3426c6:f1387822:49830fb5
   devices=/dev/sdb,/dev/sdc\n"""
                              },
                              'find_block_devs': {"9:127": "/dev/md/md-name-test:123",
                                                  "9:128": "/dev/md/md-name-test:1"
                              },
                              'results': [{
                                              'uuid': '15054135:be3426c6:f1387822:49830fb5',
                                              'path': '/dev/md/md-name-test:123',
                                              'mm': '9:127',
                                              'device_paths': ['/dev/sdb', '/dev/sdc']
                                          },
                                          {
                                              'uuid': '15054135:be3426c6:f1387822:49830fb6',
                                              'path': '/dev/md/md-name-test:1',
                                              'mm': '9:128',
                                              'device_paths': ['/dev/sdd']
                                          }],
                              'normalized_names': {"/dev/sdd": "/dev/md/md-name-test:1",
                                                   "/dev/md/md-name-test:1": "/dev/md/md-name-test:1",
                                                   "/dev/sdb": "/dev/md/md-name-test:123",
                                                   "/dev/sdc": "/dev/md/md-name-test:123",
                                                   "/dev/md/md-name-test:123": "/dev/md/md-name-test:123"}
        }

    def _load(self, filename):
        return open(os.path.join(self.test_root, filename)).read()

    def _load_dmsetup(self, devices_filename, dmsetup_filename):
        self.devices_data = json.loads(self._load(devices_filename))
        self.dmsetup_data = self._load(dmsetup_filename)

        return MockDmsetupTable(self.dmsetup_data, self.devices_data)

    def mock_debug(self, value):
        print value

    class mock_open:
        md_value = None

        def __init__(self, fname):
            pass

        def read(self):
            return self.md_value["mdstat"]

    def mock_try_run(self, arg_list):
        return self.md_value["mdadm"][arg_list[4]]

    def mock_path_to_major_minor(self, path):
        if path in self.devices_data['node_block_devices']:
            return self.devices_data['node_block_devices'][path]
        else:
            return None

    def mock_find_block_devs(self, folder):
        return self.md_value["find_block_devs"]

    def _setup_md_raid(self, devices_filename, dmsetup_filename, md_value):
        dm_setup_table = self._load_dmsetup(devices_filename, dmsetup_filename)
        dm_setup_table.block_devices.path_to_major_minor = self.mock_path_to_major_minor

        with mock.patch('logging.Logger.debug', self.mock_debug):
            with mock.patch('chroma_agent.lib.shell.AgentShell.try_run', self.mock_try_run):
                with mock.patch('__builtin__.open', self.mock_open):
                    with mock.patch('chroma_agent.device_plugins.linux_components.block_devices.BlockDevices.find_block_devs',
                                    self.mock_find_block_devs):

                        self.md_value = md_value
                        self.mock_open.md_value = md_value

                        return MdRaid(dm_setup_table.block_devices).all()

    def test_mdraid_pass(self):
        mds = self._setup_md_raid('devices_MdRaid_EMCPower.json', 'dmsetup_MdRaid_EMCPower.json', self.md_value_good)

        self.assertTrue(len(mds) == len(self.md_value_good['results']))

        for value in self.md_value_good['results']:
            uuid = value['uuid']
            self.assertTrue(uuid in mds)
            self.assertTrue(mds[uuid]['path'] == value['path'])
            self.assertTrue(mds[uuid]['block_device'] == value['mm'])
            self.assertTrue(len(mds[uuid]['drives']) == len(value['device_paths']))
            for i in range(0, len(value['device_paths'])):
                self.assertTrue(mds[uuid]['drives'][i] == self.mock_path_to_major_minor(value['device_paths'][i]))

        self.assertNormalizedPaths(self.md_value_good['normalized_names'])

    # This should not fail as such, but the dmsetup data doesn't contain the device info for the md device so the
    # data is inconsistent. The code should deal with this and return an mddevice with empty drives..
    def test_mdraid_fail(self):
        mds = self._setup_md_raid('devices_HYD-1385.json', 'dmsetup_HYD-1385.json', self.md_value_good)

        # No data should come back
        self.assertTrue(len(mds) == 0)
