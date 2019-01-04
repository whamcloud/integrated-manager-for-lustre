import logging
import json
import sys

from testconfig import config
from tests.integration.core.utility_testcase import UtilityTestCase
from tests.integration.utils.test_blockdevices.test_blockdevice import TestBlockDevice
from tests.integration.utils.test_filesystems.test_filesystem import TestFileSystem

logger = logging.getLogger("test")
logger.setLevel(logging.DEBUG)


class CreateLustreFilesystem(UtilityTestCase):
    """
    Create a lustre filesystem from the specification in the cluster config json,
    suitable to be used a lustre filesystem in the existing filesystem
    integration tests.
    """

    def setUp(self):
        super(CreateLustreFilesystem, self).setUp()

        self._setup_ha_config()

        self.fsname = config["filesystem"]["name"]

        self.mgts = self.get_targets_by_kind("MGT")
        self.assertEqual(len(self.mgts), 1)
        self.mgt = self.mgts[0]

        self.mdts = self.get_targets_by_kind("MDT")
        # would be nice to able do to this:
        # if not dne:
        #     self.assertEqual(len(self.mdts), 1)
        # else:
        #     ...
        # but until we have that flag in the config, assert that we got
        # at least one
        self.assertGreaterEqual(len(self.mdts), 1)

        # If we have a combined mdt/mgt then find it and set mdt to it.
        self.combined_mgt_mdt = None
        for mdt in self.mdts:
            if self.mgt["primary_server"] == mdt["primary_server"] and self.mgt["mount_path"] == mdt["mount_path"]:
                self.combined_mgt_mdt = mdt
                break

        self.osts = self.get_targets_by_kind("OST")
        self.assertGreaterEqual(len(self.osts), 1)

        self._clear_current_target_devices()

    def _setup_ha_config(self):
        """
        This routine changes the config so that HA nodes etc are provided. Simplistically it just sets the failover node
        to be something. Also if lvm then it turns off all the HA stuff. This is a fixup until we have HA provided as input.
        The input presumably being created by the provisioner.
        """
        is_lvm = any(server["device_type"] == "lvm" for server in config["lustre_servers"])

        if config["test_ha"] and not is_lvm:
            # Go through and find a secondary for each server, all storage is shared so any will do.
            # # Try to assign secondary nodes using as fair a distribution as we can
            # TODO: while this does provide an even distribution it seems  to
            #       break this test.  figure out why
            # assigned_secondaries = set()
            # for target in config['filesystem']['targets'].values():
            #     if len(assigned_secondaries) == len(config['lustre_servers']):
            #         assigned_secondaries.clear()
            #     for server in config['lustre_servers']:
            #         if (server['nodename'] != target['primary_server']) and \
            #            (server['nodename'] not in assigned_secondaries):
            #             target['secondary_server'] = server['nodename']
            #             assigned_secondaries.add(target['secondary_server'])
            #             break
            # This loop gives a really bad distribution, but we only use a few servers so it achieves what we need today.
            for target in config["filesystem"]["targets"].values():
                secondary_server = next(
                    server for server in config["lustre_servers"] if server["nodename"] != target["primary_server"]
                )

                target["secondary_server"] = secondary_server["nodename"]
                target["secondary_lnet_address"] = secondary_server["lnet_address"]
        else:
            config["test_ha"] = False  # Deals is is_lvm = True

            for target in config["filesystem"]["targets"].values():
                for key in ["mount_server", "secondary_server", "failover_mode", "secondary_lnet_address"]:
                    if key in target:
                        del target[key]

    def _clear_current_target_devices(self):
        for server in config["lustre_servers"]:
            self.remote_command(server["address"], "umount -t lustre -a")

            self.umount_devices(server["nodename"])

            self.execute_commands(
                TestBlockDevice.all_clear_device_commands(server["device_paths"]), server["address"], "clear command"
            )

            self.remote_command(
                server["address"],
                """
                modprobe lnet
                lnetctl lnet configure

                if [[ $(lnetctl net show --net tcp0 | wc -c) -eq 0 ]]; then
                    lnetctl net add --net tcp0 --if eth2
                    lnetctl net show --net tcp > /etc/lnet.conf
                    systemctl enable lnet.service
                fi
                """,
            )

        # Wipe the devices to make sure they are clean only after
        # all of the per server cleanup has been done. Otherwise some of the
        # commands in clear_device_commands won't get to do all that they are
        # supposed to (eg, lvremove removing lvm metadata).

        next((self.clear_devices(x["nodename"]) for x in config["lustre_servers"]), None)

        self.used_devices = []

    def _save_modified_config(self):
        """
        Save the configuration to a file that matches the current configuration with the addition of _result in it.

        Failure will cause an exception of some sort!
        """

        for idx, arg in enumerate(sys.argv):
            if arg.startswith("--tc-file="):
                filename = arg.split("=")[1]
                break
            if arg == "--tc-file":
                filename = sys.argv[idx + 1]
                break

        filename = filename.replace(".", "_updated_configuration.")

        with open(filename, "w") as outfile:
            json.dump(config, outfile, indent=2, separators=(",", ": "))

    def create_lustre_filesystem_for_test(self):
        # for the moment efs tests are not run with mixed device types
        # therefore install on all hosts straightaway
        def get_hosts(target):
            host_list = [target["primary_server"]]
            if "secondary_server" in target:
                host_list.append(target["secondary_server"])
            return host_list

        hosts = get_hosts(self.mgt)
        device_type = self.get_lustre_server_by_name(hosts[0])["device_type"]

        [hosts.extend(get_hosts(mdt)) for mdt in self.mdts if mdt != self.combined_mgt_mdt]
        [hosts.extend(get_hosts(ost)) for ost in self.osts]

        block_device = TestBlockDevice(device_type, "")

        self.execute_simultaneous_commands(
            block_device.install_packages_commands, hosts, "install blockdevice packages"
        )

        self.configure_target_device(
            self.mgt, "mgt", self.fsname, None, ["--mdt" if self.combined_mgt_mdt else "", "--mgs"]
        )

        try:
            mgs_nids = [self.get_lustre_server_by_name(self.mgt["primary_server"])["lnet_address"]]

            if "secondary_server" in self.mgt:
                mgs_nids.append(self.get_lustre_server_by_name(self.mgt["secondary_server"])["lnet_address"])
        except:
            raise RuntimeError("Could not get 'lnet_address' for %s" % self.mgt["primary_server"])

        for index, mdt in enumerate(self.mdts):
            if mdt != self.combined_mgt_mdt:
                self.configure_target_device(mdt, "mdt", self.fsname, mgs_nids, ["--mdt"])

        for ost in self.osts:
            self.configure_target_device(ost, "ost", self.fsname, mgs_nids, ["--ost"])

        for server in config["lustre_servers"]:
            self.remote_command(server["address"], "partprobe || true; udevadm settle; sync; sync")

        self._save_modified_config()

    def get_targets_by_kind(self, kind):
        return [v for _, v in config["filesystem"]["targets"].iteritems() if v["kind"] == kind]

    def get_lustre_server_by_name(self, nodename):
        for lustre_server in config["lustre_servers"]:
            if lustre_server["nodename"] == nodename:
                return lustre_server

        return None

    def get_unused_device(self, server_name):
        lustre_server = self.get_lustre_server_by_name(server_name)
        for device in lustre_server["device_paths"]:
            if device not in self.used_devices:
                return device

    def umount_devices(self, server_name):
        lustre_server = self.get_lustre_server_by_name(server_name)
        for device in lustre_server["device_paths"]:
            self.remote_command(server_name, "if mount | grep %s; then umount %s; fi;" % (device, device))

        self.remote_command(server_name, "sed -i '/lustre/d' /etc/fstab")

        self.remote_command(server_name, "systemctl daemon-reload")

    def clear_devices(self, server_name):
        lustre_server = self.get_lustre_server_by_name(server_name)
        for device in lustre_server["device_paths"]:
            self.remote_command(server_name, "wipefs -a {0}".format(device))

    def rename_device(self, device_old_path, device_new_path):
        for lustre_server in config["lustre_servers"]:
            lustre_server["device_paths"] = [
                device if device != device_old_path else device_new_path for device in lustre_server["device_paths"]
            ]

    def mount_target(self, block_device, target, device):
        # If failnode was used, then we must mount the primary before mounting the secondary, so if the secondary is the target mount mount
        # and umount the primary.
        #
        # When this routine is called the target must be accessible from the primary_target
        if (target.get("failover_mode") == "failnode") and (target.get("mount_server") == "secondary_server"):
            self.remote_command(target["primary_server"], "systemctl daemon-reload")
            self.remote_command(target["primary_server"], "mkdir -p %s" % target["mount_path"])
            self.remote_command(target["primary_server"], "mount -t lustre %s %s" % (device, target["mount_path"]))
            self.remote_command(target["primary_server"], "umount %s" % target["mount_path"])

        target_server = target[target.get("mount_server", "primary_server")]

        self.remote_command(target_server, "systemctl daemon-reload")

        # If we are going to mount on the secondary the move the block device from the primary to the secondary.
        if target.get("mount_server") == "secondary_server":
            self.execute_commands(block_device.release_commands, target["primary_server"], "Release device")
            self.execute_commands(block_device.capture_commands, target["secondary_server"], "Capture device")

        self.remote_command(target_server, "mkdir -p %s" % target["mount_path"])
        self.remote_command(target_server, "mount -t lustre %s %s" % (device, target["mount_path"]))
        self.remote_command(
            target_server,
            "echo '%s   %s  lustre  defaults,_netdev    0 0' >> /etc/fstab" % (device, target["mount_path"]),
        )

    def configure_target_device(self, target, target_type, fsname, mgs_nids, mkfs_options):

        targets = {"primary_server": target["primary_server"]}

        if "secondary_server" in target:
            targets["secondary_server"] = target["secondary_server"]

        device_path = self.get_unused_device(targets["primary_server"])
        device_type = self.get_lustre_server_by_name(targets["primary_server"])["device_type"]

        block_device = TestBlockDevice(device_type, device_path)

        self.execute_commands(block_device.reset_device_commands, targets["primary_server"], "reset device")

        filesystem = TestFileSystem(block_device.preferred_fstype, block_device.device_path)

        result = self.remote_command(
            targets["primary_server"], filesystem.mkfs_command(target, target_type, fsname, mgs_nids, mkfs_options)
        )

        logger.info("mkfs.lustre output:\n %s" % result.stdout)

        self.rename_device(device_path, filesystem.mount_path)
        self.used_devices.append(filesystem.mount_path)

        self.mount_target(block_device, target, filesystem.mount_path)

        return filesystem.mount_path
