from django.utils.unittest import skipIf

from testconfig import config
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase
from tests.integration.utils.test_blockdevices.test_blockdevice import TestBlockDevice


@skipIf(config.get('simulator', False), "Can't setup ZFS pools on the simulator")
class TestConfigureZfsTargets(ChromaIntegrationTestCase):
    """
    Not a test as such but a method for turning some of the disks into zpools.
    """
    def test_setup_zfs_targets_for_test(self):
        if self.zfs_devices_exist is False:
            return

        first_test_server = self.config_servers[0]

        # We add the hosts to cause ZFS to be installed.
        self.add_hosts([server['address'] for server in self.config_servers])

        self.cleanup_zfs_pools(self.config_servers, True, None, False)

        for lustre_device in config['lustre_devices']:
            if lustre_device['backend_filesystem'] == 'zfs':
                zfs_device = TestBlockDevice('zfs', first_test_server['device_paths'][lustre_device['path_index']])

                self.execute_commands(zfs_device.prepare_device_commands,
                                      first_test_server['fqdn'],
                                      'create zfs device %s' % zfs_device)

                # Replace the name with the new name on each server, replace this way to ensure
                # the order is not changed
                for server in config['lustre_servers']:
                    server['device_paths'][lustre_device['path_index']] = zfs_device.device_path
