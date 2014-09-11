#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2014 Intel Corporation All Rights Reserved.
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


import os
import re
import subprocess
from tempfile import mktemp
from collections import defaultdict
from datetime import datetime

from chroma_agent.chroma_common.lib import shell
from chroma_agent.utils import Mounts
import chroma_agent.lib.normalize_device_path as ndp
from chroma_agent.chroma_common.blockdevices.blockdevice import BlockDevice
from chroma_agent.log import daemon_log
from chroma_agent import config


class LocalTargets(object):
    '''
    Allows local targets to be examined. Not the targets are only examined once with the results cached. Detecting change
    therefore requires a new instance to be created and queried.
    '''

    def __init__(self, target_devices):
        self.targets = self._get_targets(target_devices)

    def _get_targets(self, target_devices):
        # Working set: accumulate device paths for each (uuid, name).  This is
        # necessary because in multipathed environments we will see the same
        # lustre target on more than one block device.  The reason we use name
        # as well as UUID is that two logical targets can have the same UUID
        # when we see a combined MGS+MDT
        uuid_name_to_target = {}

        for device in target_devices:
            daemon_log.info("Searching device %s of type %s, uuid %s for a Lustre filesystem" % (device['path'], device['type'], device['uuid']))

            # If the target_device has no uuid then it doesn't have a filesystem and is of no use to use, but
            # for now let's fill it in an see what happens.
            if device['uuid'] == None:
                try:
                    device['uuid'] = BlockDevice(device['type'], device['path']).uuid
                except shell.CommandExecutionError:
                    # Not even got a GUID so not going to have a lustre filesystem.
                    continue

            # OK, so we really don't have a uuid for this, so we won't find a lustre filesystem on it.
            if device['uuid'] == None:
                daemon_log.info("Device %s had no UUID and so will not be examined for Lustre" % device['path'])
                continue

            rc, tunefs_text, stderr = shell.run(["tunefs.lustre", "--dryrun", device['path']])
            if rc != 0:
                daemon_log.info("Device %s did not have a Lustre filesystem on it" % device['path'])
                continue

            # For a Lustre block device, extract name and params
            # ==================================================
            name = re.search("Target:\\s+(.*)\n", tunefs_text).group(1)
            flags = int(re.search("Flags:\\s+(0x[a-fA-F0-9]+)\n", tunefs_text).group(1), 16)
            params_re = re.search("Parameters:\\ ([^\n]+)\n", tunefs_text)
            if params_re:
                # Dictionary of parameter name to list of instance values
                params = {}
                # FIXME: naive parse: can these lines be quoted/escaped/have spaces?
                for param, value in [t.split('=') for t in params_re.group(1).split()]:
                    if not param in params:
                        params[param] = []
                    params[param].append(value)
            else:
                params = {}

            if name.find("ffff") != -1:
                daemon_log.info("Device %s reported an unregistered lustre target and so will not be reported" % device['path'])
                continue

            mounted = ndp.normalized_device_path(device['path']) in set([ndp.normalized_device_path(path) for path, _, _ in Mounts().all()])

            if flags & 0x0005 == 0x0005:
                # For combined MGS/MDT volumes, synthesise an 'MGS'
                names = ["MGS", name]
            else:
                names = [name]

            for name in names:
                daemon_log.info("Device %s contained name:%s and is %smounted" % (device['path'], name, "" if mounted else "un"))

                try:
                    target_dict = uuid_name_to_target[(device['uuid'], name)]
                    target_dict['devices'].append(device)
                except KeyError:
                    target_dict = {"name": name,
                                   "uuid": device['uuid'],
                                   "params": params,
                                   "device_paths": [device['path']],
                                   "mounted": mounted}
                    uuid_name_to_target[(device['uuid'], name)] = target_dict

        return uuid_name_to_target.values()


class MgsTargets(object):
    TARGET_NAME_REGEX = "([\w-]+)-(MDT|OST)\w+"

    def __init__(self, local_targets):
        super(MgsTargets, self).__init__()
        self.filesystems = defaultdict(lambda: [])
        self.conf_params = defaultdict(lambda: defaultdict(lambda: {}))

        self._get_targets(local_targets)

    def _get_targets(self, local_targets):
        """If there is an MGS in the local targets, use debugfs to
           get a list of targets.  Return a dict of filesystem->(list of targets)"""

        mgs_target = None

        for t in local_targets:
            if t["name"] == "MGS" and t['mounted']:
                mgs_target = t

        if not mgs_target:
            return

        device_path = mgs_target["device_paths"][0]

        daemon_log.info("Searching Lustre logs for filesystems")

        ls = shell.try_run(["debugfs", "-c", "-R", "ls -l CONFIGS/", device_path])
        filesystems = []
        targets = []
        for line in ls.split("\n"):
            try:
                name = line.split()[8]

                match = re.search("([\w-]+)-client", name)
                if match is not None:
                    daemon_log.info("Found a filesystem of name %s" % match.group(1).__str__())
                    filesystems.append(match.group(1).__str__())

                match = re.search(self.TARGET_NAME_REGEX, name)
                if match is not None:
                    daemon_log.info("Found a target of name %s" % match.group(0).__str__())
                    targets.append(match.group(0).__str__())
            except IndexError:
                pass

        # Read config log "<fsname>-client" for each filesystem
        for fs in filesystems:
            self._read_log("filesystem", fs, "%s-client" % fs, device_path)
            self._read_log("filesystem", fs, "%s-param" % fs, device_path)

        # Read config logs "testfs-MDT0000" etc
        for target in targets:
            self._read_log("target", target, target, device_path)

    def _read_log(self, conf_param_type, conf_param_name, log_name, dev):
        # NB: would use NamedTemporaryFile if we didn't support python 2.4
        """
        Uses debugfs to parse information about the filesystem on a device. Return any mgs info
        and config parameters about that device.

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

        daemon_log.info("Reading log for %s:%s from log %s" % (conf_param_type, conf_param_name, log_name))

        try:
            shell.try_run(["debugfs", "-c", "-R", "dump CONFIGS/%s %s" % (log_name, tmpfile), dev])
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

                    daemon_log.info("Found log entry for uuid %s, label %s, nid %s" % (uuid, label, nid))

                    self.filesystems[fs_name].append({
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

                    daemon_log.info("Found conf param %s:%s:%s of %s" % (param_type, param_name, key, val))

                    self.conf_params[param_type][param_name][key] = val
        finally:
            if os.path.exists(tmpfile):
                os.unlink(tmpfile)


def detect_scan(target_devices=None):
    """Look for Lustre on possible devices

    Save the input devices when possible.  Then future calls will
    not need to specify the target_devices
    """

    right_now = str(datetime.now())

    if target_devices is not None:
        target_devices_time_stamped = dict(timestamp=right_now, target_devices=target_devices)
        config.update('settings', 'last_detect_scan_target_devices', target_devices_time_stamped)

    try:
        # Recall the last target_devices used in this method
        settings = config.get('settings', 'last_detect_scan_target_devices')
    except KeyError:
        # This method was never called with a non-null target_devices
        # or the setting file holding the device record is not found.
        daemon_log.warn("detect_scan improperly called without target_devices "
                        "and without a previous call's target_devices to use.")

        # TODO: Consider an exception here. But, since this is a rare case, it seems reasonable to return emptiness
        # TODO: If this raised an exception, it should be a handled one in any client, and that seems too heavy
        local_targets = LocalTargets([])
        timestamp = right_now

    else:
        # Have target devices, so process them
        timestamp = settings['timestamp']
        daemon_log.info("detect_scan called at %s with target_devices saved on %s" % (str(datetime.now()), timestamp))
        local_targets = LocalTargets(settings['target_devices'])

    # Return the discovered Lustre components on the target devices, may return emptiness.
    mgs_targets = MgsTargets(local_targets.targets)
    return {"target_devices_saved_timestamp": timestamp,
            "local_targets": local_targets.targets,
            "mgs_targets": mgs_targets.filesystems,
            "mgs_conf_params": mgs_targets.conf_params}


ACTIONS = [detect_scan]
CAPABILITIES = []
