# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import re
import os
import subprocess
from collections import defaultdict
from tempfile import mktemp

from blockdevice import BlockDevice
from ..lib import shell


class BlockDeviceLinux(BlockDevice):
    _supported_device_types = ['linux']
    TARGET_NAME_REGEX = "([\w-]+)-(MDT|OST)\w+"

    def __init__(self, device_type, device_path):
        super(BlockDeviceLinux, self).__init__(device_type, device_path)

        self._modules_initialized = False

    def _initialize_modules(self):
        if not self._modules_initialized:
            try:                                            # osd_ldiskfs will load ldiskfs in Lustre 2.4.0+
                shell.Shell.try_run(['modprobe', 'osd_ldiskfs'])  # TEI-469: Race loading the osd module during mkfs.lustre
            except shell.Shell.CommandExecutionError:
                shell.Shell.try_run(['modprobe', 'ldiskfs'])      # TEI-469: Race loading the ldiskfs module during mkfs.lustre

            self._modules_initialized = True

    @property
    def filesystem_type(self):
        """
        Verify if filesystem exists at self._device_path and return type

        :return: type if exists, None otherwise
        """
        occupying_fs = self._blkid_value("TYPE")

        return occupying_fs

    @property
    def filesystem_info(self):
        """
        Verify if filesystem exists at self._device_path and return message

        :return: message indicating type if exists, None otherwise
        """
        occupying_fs = self._blkid_value("TYPE")

        return None if occupying_fs is None else "Filesystem found: type '%s'" % occupying_fs

    @property
    def uuid(self):
        return self._blkid_value("UUID")

    def _blkid_value(self, value):
        result = shell.Shell.run(["blkid", "-p", "-o", "value", "-s", value, self._device_path])

        if result.rc == 2:
            # blkid returns 2 if there is no filesystem on the device
            return None
        elif result.rc == 0:
            result = result.stdout.strip()

            if result:
                return result
            else:
                # Empty filesystem: blkid returns 0 but prints no FS if it seems something non-filesystem-like
                # like an MBR
                return None
        else:
            raise RuntimeError("Unexpected return code %s from blkid %s: '%s' '%s'" % (result.rc, self._device_path, result.stdout, result.stderr))

    @property
    def preferred_fstype(self):
        return 'ldiskfs'

    def mgs_targets(self, log):
        """
        If there is an MGS in the local targets, use debugfs to get a list of targets.
        Return a dict of filesystem->(list of targets)
        """
        self._initialize_modules()

        result = defaultdict(lambda: [])

        log.info("Searching Lustre logs for filesystems")

        ls = shell.Shell.try_run(["debugfs", "-c", "-R", "ls -l CONFIGS/", self._device_path])
        filesystems = []
        targets = []
        for line in ls.split("\n"):
            try:
                name = line.split()[8]

                match = re.search("([\w-]+)-client", name)
                if match is not None:
                    log.info("Found a filesystem of name %s" % match.group(1).__str__())
                    filesystems.append(match.group(1).__str__())

                match = re.search(self.TARGET_NAME_REGEX, name)
                if match is not None:
                    log.info("Found a target of name %s" % match.group(0).__str__())
                    targets.append(match.group(0).__str__())
            except IndexError:
                pass

        # Read config log "<fsname>-client" for each filesystem
        for fs in filesystems:
            self._read_log("filesystem", fs, "%s-client" % fs, result, log)
            self._read_log("filesystem", fs, "%s-param" % fs, result, log)

        # Read config logs "testfs-MDT0000" etc
        for target in targets:
            self._read_log("target", target, target, result, log)

        return result

    def _read_log(self, conf_param_type, conf_param_name, log_name, result, log):
        # NB: would use NamedTemporaryFile if we didn't support python 2.4
        """
        Uses debugfs to parse information about the filesystem on a device. Return any mgs info
        and config parameters about that device.

        The reality is that nothing makes use of the conf_params anymore but the code existed and this routine
        is unchanged from before 2.0 so I have left conf_params in.

        :param conf_param_type: The type of configuration parameter to store
        :type conf_param_type: str
        :param conf_param_name: The name of the configuration parameter to store
        :type conf_param_name: dict
        :param log_name: The log name to dump the information about dev into
        :type log_name: str
        :param dev: The dev[vice] to parse for log information
        :type dev: str

        Returns: MgsTargetInfo containing targets and conf found.
        """

        tmpfile = mktemp()

        log.info("Reading log for %s:%s from log %s" % (conf_param_type, conf_param_name, log_name))

        try:
            shell.Shell.try_run(["debugfs", "-c", "-R", "dump CONFIGS/%s %s" % (log_name, tmpfile), self._device_path])
            if not os.path.exists(tmpfile) or os.path.getsize(tmpfile) == 0:
                # debugfs returns 0 whether it succeeds or not, find out whether
                # dump worked by looking for output file of some length. (LU-632)
                return

            client_log = subprocess.Popen(["llog_reader", tmpfile], stdout=subprocess.PIPE).stdout.read()

            entries = client_log.split("\n#")[1:]
            for entry in entries:
                tokens = entry.split()
                # ([\w=]+) covers all possible token[0] from
                # lustre/utils/llog_reader.c @ 0f8dca08a4f68cba82c2c822998ecc309d3b7aaf
                (code, action) = re.search("^\\((\d+)\\)([\w=]+)$", tokens[1]).groups()
                if conf_param_type == 'filesystem' and action == 'setup':
                    # e.g. entry="#09 (144)setup     0:flintfs-MDT0000-mdc  1:flintfs-MDT0000_UUID  2:192.168.122.105@tcp"
                    label = re.search("0:([\w-]+)-\w+", tokens[2]).group(1)
                    fs_name = label.rsplit("-", 1)[0]
                    uuid = re.search("1:(.*)", tokens[3]).group(1)
                    nid = re.search("2:(.*)", tokens[4]).group(1)

                    log.info("Found log entry for uuid %s, label %s, nid %s" % (uuid, label, nid))

                    result[fs_name].append({
                        "uuid": uuid,
                        "name": label,
                        "nid": nid})
                elif action == "param" or (action == 'SKIP' and tokens[2] == 'param'):
                    if action == 'SKIP':
                        clear = True
                        tokens = tokens[1:]
                    else:
                        clear = False

                    # e.g. entry="#29 (112)param 0:flintfs-client  1:llite.max_cached_mb=247.9"
                    # has conf_param name "flintfs.llite.max_cached_mb"
                    object = tokens[2][2:]
                    if len(object) == 0:
                        # e.g. "0: 1:sys.at_max=1200" in an OST log: it is a systemwide
                        # setting
                        param_type = conf_param_type
                        param_name = conf_param_name
                    elif re.search(self.TARGET_NAME_REGEX, object):
                        # Identify target params
                        param_type = 'target'
                        param_name = re.search(self.TARGET_NAME_REGEX, object).group(0)
                    else:
                        # Fall through here for things like 0:testfs-llite, 0:testfs-clilov
                        param_type = conf_param_type
                        param_name = conf_param_name

                    if tokens[3][2:].find("=") != -1:
                        key, val = tokens[3][2:].split("=")
                    else:
                        key = tokens[3][2:]
                        val = True

                    if clear:
                        val = None

                    log.info("Found conf param %s:%s:%s of %s" % (param_type, param_name, key, val))

                    # 2.2 don't save the conf params because nothing reads them and zfs doesn't seem to produce them
                    # so keep the code - but just don't store.
                    # This change is being made on the FF date hence the caution.
                    #self.conf_params[param_type][param_name][key] = val
        finally:
            if os.path.exists(tmpfile):
                os.unlink(tmpfile)

    def targets(self, uuid_name_to_target, device, log):
        self._initialize_modules()

        log.info("Searching device %s of type %s, uuid %s for a Lustre filesystem" % (device['path'], device['type'], device['uuid']))

        result = shell.Shell.run(["tunefs.lustre", "--dryrun", device['path']])
        if result.rc != 0:
            log.info("Device %s did not have a Lustre filesystem on it" % device['path'])
            return self.TargetsInfo([], None)

        # For a Lustre block device, extract name and params
        # ==================================================
        name = re.search("Target:\\s+(.*)\n", result.stdout).group(1)
        flags = int(re.search("Flags:\\s+(0x[a-fA-F0-9]+)\n", result.stdout).group(1), 16)
        params_re = re.search("Parameters:\\ ([^\n]+)\n", result.stdout)
        if params_re:
            # Dictionary of parameter name to list of instance values
            params = defaultdict(list)

            # FIXME: naive parse: can these lines be quoted/escaped/have spaces?
            for lustre_property, value in [t.split('=') for t in params_re.group(1).split()]:
                params[lustre_property].extend(re.split(BlockDeviceLinux.lustre_property_delimiters[lustre_property], value))
        else:
            params = {}

        if name.find("ffff") != -1:
            log.info("Device %s reported an unregistered lustre target and so will not be reported" % device['path'])
            return self.TargetsInfo([], None)

        if flags & 0x0005 == 0x0005:
            # For combined MGS/MDT volumes, synthesise an 'MGS'
            names = ["MGS", name]
        else:
            names = [name]

        return self.TargetsInfo(names, params)
