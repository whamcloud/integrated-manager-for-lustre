import logging

from testconfig import config
from tests.integration.core.utility_testcase import UtilityTestCase


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
                'modprobe lnet; lctl network up; modprobe lustre; umount -t lustre -a'
            )

        used_devices = []

        combined_mgt_mdt = mgt['primary_server'] == mdt['primary_server'] and mgt['mount_path'] == mdt['mount_path']

        mgt_device = self.get_unused_device(mgt['primary_server'], used_devices)
        result = self.remote_command(
            mgt['primary_server'],
            'mkfs.lustre --reformat --fsname=%s --mgs %s %s' % (fsname, '--mdt' if combined_mgt_mdt else '', mgt_device)
        )
        logger.info("mkfs.lustre output:\n %s" % result.stdout.read())
        used_devices.append(mgt_device)
        self.mount_target(mgt, mgt_device)
        try:
            mgs_ip = self.get_lustre_server_by_name(mgt['primary_server'])['ip_address']
        except:
            raise RuntimeError("Could not get 'ip_address' for %s" %
                               mgt['primary_server'])

        if not combined_mgt_mdt:
            # TODO: Create the separate MDT
            raise RuntimeError("Separate MGT and MDT configuration not implemented yet.")

        for ost in osts:
            ost_device = self.get_unused_device(ost['primary_server'], used_devices)
            result = self.remote_command(
                ost['primary_server'],
                'mkfs.lustre --reformat --ost --fsname=%s --mgsnode=%s@tcp0 %s' % (fsname, mgs_ip, ost_device)
            )
            logger.info("mkfs.lustre output:\n %s" % result.stdout.read())
            used_devices.append(ost_device)
            self.mount_target(ost, ost_device)

        for server in config['lustre_servers']:
            self.remote_command(
                server['address'],
                'sync; sync'
            )

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
