from django.utils.unittest import skipIf

from testconfig import config
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase
from tests.integration.utils.test_blockdevices.test_blockdevice import TestBlockDevice


@skipIf(config.get('simulator', False), "Can't setup ZFS pools on the simulator")
class TestConfigureZfsTargets(ChromaIntegrationTestCase):
    """
    Not a test as such but a method for turning some of the disks into zpools.
    """
    @property
    def quick_setup(self):
        """
        This test use quick_setup because at the time of this call no-zfs pools exist and so
        the cleanup routine in the regular setup will fail.

        It is probably the only case where quick_setup should be used outside of local debug.

        :return: True to indicate quicksetup should be used.
        """
        return True

    def test_setup_zfs_targets_for_test(self):
        if self.zfs_devices_exist() is False:
            return

        # We add the hosts to cause ZFS to be installed.
        self.add_hosts([server['address'] for server in self.config_servers])

        # Replace the name with the new name on each server, replace this way to ensure the order is not changed
        for server in config['lustre_servers']:
            server['zpool_device_paths'] = {}

            for lustre_device in config['lustre_devices']:
                if lustre_device['backend_filesystem'] == 'zfs':
                    zfs_device = TestBlockDevice('zfs', server['device_paths'][lustre_device['path_index']])

                    # Make copy of the original to use when creating/recreating the zpools or for anything
                    # else that needs original device.
                    server['zpool_device_paths'][lustre_device['path_index']] = server['device_paths'][lustre_device['path_index']]
                    server['device_paths'][lustre_device['path_index']] = zfs_device.device_path

        self.cleanup_zfs_pools(self.config_servers, self.CZP_RECREATEZPOOLS | self.CZP_EXPORTPOOLS, None, False)
