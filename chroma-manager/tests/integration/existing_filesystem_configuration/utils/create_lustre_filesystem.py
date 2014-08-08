import logging
import os
import json

from testconfig import config
from tests.integration.core.utility_testcase import UtilityTestCase
from tests.integration.utils.test_blockdevices.test_blockdevice import TestBlockDevice
from tests.integration.utils.test_filesystems.test_filesystem import TestFileSystem


logger = logging.getLogger('test')
logger.setLevel(logging.DEBUG)


class CreateLustreFilesystem(UtilityTestCase):
    """
    Create a lustre filesystem from the specification in the cluster config json,
    suitable to be used a lustre filesystem in the existing filesystem
    integration tests.
    """

    def create_lustre_filesystem_for_test(self):
        fsname = config['filesystem']['name']

        mgts = self.get_targets_by_kind('MGT')
        self.assertTrue(1, len(mgts))
        mgt = mgts[0]

        mdts = self.get_targets_by_kind('MDT')
        self.assertTrue(1, len(mdts))
        mdt = mdts[0]

        osts = self.get_targets_by_kind('OST')
        self.assertGreaterEqual(len(osts), 1)

        for server in config['lustre_servers']:
            self.remote_command(
                server['address'],
                'umount -t lustre -a'
            )

            for command in TestBlockDevice.all_clear_device_commands():
                result = self.remote_command(server['address'],
                                             command)
                logger.info("clear command output:\n %s" % result.stdout.read())

            self.umount_devices(server['address'])
            self.dd_devices(server['address'])

            self.remote_command(server['address'],
                                'reboot',
                                expected_return_code = None)    # Sometimes reboot hangs, sometimes it doesn't

        def host_alive(hostname):
            try:
                return self.remote_command(hostname,
                                           'hostname',
                                           expected_return_code = None).exit_status == 0
            except:
                return False

        for server in config['lustre_servers']:
            self.wait_until_true(lambda: host_alive(server['address']))

            self.remote_command(
                server['address'],
                'modprobe lnet; lctl network up; modprobe lustre'
            )

        used_devices = []

        combined_mgt_mdt = mgt['primary_server'] == mdt['primary_server'] and mgt['mount_path'] == mdt['mount_path']

        self.fetch_and_configure_a_device(mgt,
                                          'mgt',
                                          None,
                                          fsname,
                                          None,
                                          ['--reformat',
                                           '--mdt' if combined_mgt_mdt else '',
                                           '--mgs'],
                                          used_devices)

        try:
            mgs_ip = self.get_lustre_server_by_name(mgt['primary_server'])['ip_address']
        except:
            raise RuntimeError("Could not get 'ip_address' for %s" %
                               mgt['primary_server'])

        if not combined_mgt_mdt:
            # TODO: Create the separate MDT
            raise RuntimeError("Separate MGT and MDT configuration not implemented yet.")

        for index, ost in enumerate(osts):
            for command in TestBlockDevice.clear_device_commands():
                result = self.remote_command(ost['primary_server'],
                                             command)
                logger.info("clear command output:\n %s" % result.stdout.read())

            self.fetch_and_configure_a_device(ost,
                                              'ost',
                                              index,
                                              fsname,
                                              mgs_ip,
                                              ['--reformat', '--ost'],
                                              used_devices)

        for server in config['lustre_servers']:
            self.remote_command(
                server['address'],
                'sync; sync'
            )

        if os.getenv('LUSTRE_FILESYSTEM_CONFIGFILE'):
            with open(os.getenv('LUSTRE_FILESYSTEM_CONFIGFILE'), 'w') as outfile:
                json.dump(config, outfile, indent = 2, separators=(',', ': '))

    def get_targets_by_kind(self, kind):
        return [v for k, v in config['filesystem']['targets'].iteritems() if v['kind'] == kind]

    def get_lustre_server_by_name(self, nodename):
        for lustre_server in config['lustre_servers']:
            if lustre_server['nodename'] == nodename:
                return lustre_server

        return None

    def get_unused_device(self, server_name, used_devices):
        lustre_server = self.get_lustre_server_by_name(server_name)
        for device in lustre_server['device_paths']:
            if device not in used_devices:
                return device

    def umount_devices(self, server_name):
        lustre_server = self.get_lustre_server_by_name(server_name)
        for device in lustre_server['device_paths']:
            self.remote_command(
                server_name,
                "if mount | grep %s; then umount %s; fi;" % (device, device))

        self.remote_command(
            server_name,
            "sed -i '/lustre/d' /etc/fstab")

    def dd_devices(self, server_name):
        lustre_server = self.get_lustre_server_by_name(server_name)
        for device in lustre_server['device_paths']:
            self.remote_command(
                server_name,
                "dd if=/dev/zero of=%s bs=512 count=1" % device)

    def rename_device(self, device_old_path, device_new_path):
        for lustre_server in config['lustre_servers']:
            lustre_server['device_paths'] = [device if device != device_old_path else device_new_path for device in lustre_server['device_paths']]

    def mount_target(self, target, device):
        self.remote_command(
            target['primary_server'],
            'mkdir -p %s' % target['mount_path']
        )
        self.remote_command(
            target['primary_server'],
            'mount -t lustre %s %s' % (device, target['mount_path'])
        )
        self.remote_command(
            target['primary_server'],
            "echo '%s   %s  lustre  defaults,_netdev    0 0' >> /etc/fstab" % (device, target['mount_path'])
        )

    def fetch_and_configure_a_device(self,
                                     target,
                                     target_type,
                                     index,
                                     fsname,
                                     mgs_ip,
                                     mkfs_options,
                                     used_devices):

        device_path = self.get_unused_device(target['primary_server'], used_devices)
        device_type = self.get_lustre_server_by_name(target['primary_server'])['device_type']

        block_device = TestBlockDevice(device_type, device_path)

        for command in block_device.install_packages_commands():
            result = self.remote_command(target['primary_server'],
                                         command)
            logger.info("install blockdevice packages command output:\n %s" % result.stdout.read())

        result = self.remote_command(target['primary_server'],
                                     block_device.prepare_device())
        logger.info("prepare output:\n %s" % result.stdout.read())

        filesystem = TestFileSystem(block_device.preferred_fstype, block_device.device_path)

        for command in filesystem.install_packages_commands():
            result = self.remote_command(target['primary_server'],
                                         command)
            logger.info("install filesystem packages command output:\n %s" % result.stdout.read())

        result = self.remote_command(target['primary_server'],
                                     filesystem.mkfs_command(target_type,
                                                             index,
                                                             fsname,
                                                             mgs_ip,
                                                             mkfs_options))

        logger.info("mkfs.lustre output:\n %s" % result.stdout.read())

        self.rename_device(device_path, filesystem.mount_path)
        used_devices.append(filesystem.mount_path)

        self.mount_target(target, filesystem.mount_path)

        return filesystem.mount_path
