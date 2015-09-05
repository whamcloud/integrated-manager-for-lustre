import json
import os

import mock
from chroma_agent.device_plugins.linux import EMCPower
from tests.device_plugins.linux.test_linux import LinuxAgentTests, MockDmsetupTable


class TestEMCPower(LinuxAgentTests):

    def setUp(self):
        super(TestEMCPower, self).setUp()

        self.emcpower_value_good = {'powermt': {"dev=emcpowera": ("VNX ID=APM00122204204 [NGS1]\n"
                                                                  "Logical device ID=600601603BC12D00C4CECB092F1FE311 [LUN 11]\n"
                                                                  "state=alive; policy=CLAROpt; queued-IOs=0\n"
                                                                  "Owner: default=SP A, current=SP A	Array failover mode: 4\n"
                                                                  "==============================================================================\n"
                                                                  "--------------- Host ---------------   - Stor -  -- I/O Path --   -- Stats ---\n"
                                                                  "###  HW Path               I/O Paths    Interf.  Mode     State   Q-IOs Errors\n"
                                                                  "==============================================================================\n"
                                                                  "  13 qla2xxx                sdb         SP A0    active   alive      0      0\n"
                                                                  "  12 qla2xxx                sde         SP B0    active   alive      0      0\n"),
                                                "dev=emcpowerbb": ("VNX ID=APM00122204204 [NGS1]\n"
                                                                   "Logical device ID=D00C4CECB600601603BC12092F1FE311 [LUN 11]\n"
                                                                   "state=alive; policy=CLAROpt; queued-IOs=0\n"
                                                                   "Owner: default=SP A, current=SP A	Array failover mode: 4\n"
                                                                   "==============================================================================\n"
                                                                   "--------------- Host ---------------   - Stor -  -- I/O Path --   -- Stats ---\n"
                                                                   "###  HW Path               I/O Paths    Interf.  Mode     State   Q-IOs Errors\n"
                                                                   "==============================================================================\n"
                                                                   "  14 qla2xxx                sdf         SP A0    active   alive      0      0\n"
                                                                   "  13 qla2xxx                sdd         SP A0    active   alive      0      0\n"
                                                                   "  12 qla2xxx                sdc         SP B0    active   alive      0      0")},
                                    'glob': {"/dev/emcpower?*": ["/dev/emcpowera", "/dev/emcpowerbb"]},
                                    'find_block_devs': {"99:12": "/dev/emcpowera",
                                                        "98:12": "/dev/emcpowerbb"},
                                    'results': [{
                                                    'uuid': '60060160:3BC12D00:C4CECB09:2F1FE311',

                                                    'path': '/dev/emcpowera',
                                                    'mm': '99:12',
                                                    'device_paths': ['/dev/sdb', '/dev/sde']
                                                },
                                                {
                                                    'uuid': 'D00C4CEC:B6006016:03BC1209:2F1FE311',
                                                    'path': '/dev/emcpowerbb',
                                                    'mm': '98:12',
                                                    'device_paths': ['/dev/sdf', '/dev/sdd', '/dev/sdc']
                                                }],
                                    'normalized_names': {"/dev/sdb": "/dev/emcpowera",
                                                         "/dev/sde": "/dev/emcpowera",
                                                         "/dev/emcpowera": "/dev/emcpowera",
                                                         "/dev/sdc": "/dev/emcpowerbb",
                                                         "/dev/sdd": "/dev/emcpowerbb",
                                                         "/dev/sdf": "/dev/emcpowerbb",
                                                         "/dev/emcpowerbb": "/dev/emcpowerbb"}
        }

    def _load(self, filename):
        return open(os.path.join(self.test_root, filename)).read()

    def _load_dmsetup(self, devices_filename, dmsetup_filename):
        self.devices_data = json.loads(self._load(devices_filename))
        self.dmsetup_data = self._load(dmsetup_filename)

        return MockDmsetupTable(self.dmsetup_data, self.devices_data)

    def mock_debug(self, value):
        print value

    def mock_try_run(self, arg_list):
        return self.emcpower_value["powermt"][arg_list[2]]

    def mock_glob(self, path):
        try:
            return self.emcpower_value["glob"][path]
        except KeyError:
            return []

    def mock_dev_major_minor(self, path):
        if path in self.devices_data['node_block_devices']:
            return self.devices_data['node_block_devices'][path]
        else:
            return None

    def mock_find_block_devs(self, folder):
        return self.emcpower_value["find_block_devs"]

    def _setup_emcpower(self, devices_filename, dmsetup_filename, emcpower_value):
        dm_setup_table = self._load_dmsetup(devices_filename, dmsetup_filename)

        with mock.patch('logging.Logger.debug', self.mock_debug):
            with mock.patch('glob.glob', self.mock_glob):
                with mock.patch('chroma_agent.lib.shell.AgentShell.try_run', self.mock_try_run):
                    with mock.patch('chroma_agent.device_plugins.linux.DeviceHelper._dev_major_minor', self.mock_dev_major_minor):
                        with mock.patch('chroma_agent.device_plugins.linux.DeviceHelper._find_block_devs', self.mock_find_block_devs):

                            self.emcpower_value = emcpower_value

                            return EMCPower(dm_setup_table.block_devices).all()

    def test_emcpower_pass(self):
        emcpowers = self._setup_emcpower('devices_MdRaid_EMCPower.json', 'dmsetup_MdRaid_EMCPower.json', self.emcpower_value_good)

        self.assertTrue(len(emcpowers) == len(self.emcpower_value_good['results']))

        for value in self.emcpower_value_good['results']:
            uuid = value['uuid']
            self.assertTrue(uuid in emcpowers)
            self.assertTrue(emcpowers[uuid]['path'] == value['path'])
            self.assertTrue(emcpowers[uuid]['block_device'] == value['mm'])
            self.assertTrue(len(emcpowers[uuid]['drives']) == len(value['device_paths']))
            for i in range(0, len(value['device_paths'])):
                self.assertTrue(emcpowers[uuid]['drives'][i] == self.mock_dev_major_minor(value['device_paths'][i]))

        self.assertNormalizedPaths(self.emcpower_value_good['normalized_names'])

    # This should not fail as such, but the data doesn't contain the emcpower info for the so the
    # data is inconsistent. The code should deal with this and return an emcpowers with empty drives..
    def test_emcpower_fail(self):
        emcpowers = self._setup_emcpower('devices_HYD-1385.json', 'dmsetup_HYD-1385.json', self.emcpower_value_good)

        # No data should come back
        self.assertTrue(len(emcpowers) == 0)
