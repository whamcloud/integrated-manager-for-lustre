#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import os
import re
import subprocess

from chroma_agent.utils import normalize_device, Mounts, BlkId
from chroma_agent import shell


def get_local_targets():
    # Working set: accumulate device paths for each (uuid, name).  This is
    # necessary because in multipathed environments we will see the same
    # lustre target on more than one block device.  The reason we use name
    # as well as UUID is that two logical targets can have the same UUID
    # when we see a combined MGS+MDT
    uuid_name_to_target = {}

    for blkid_device in BlkId().all():
        dev = normalize_device(blkid_device['path'])

        rc, tunefs_text, stderr = shell.run(["tunefs.lustre", "--dryrun", dev])
        if rc != 0:
            # Not lustre
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
            # Do not report unregistered lustre targets
            continue

        mounted = dev in set([normalize_device(m[0]) for m in Mounts().all()])

        if flags & 0x0005 == 0x0005:
            # For combined MGS/MDT volumes, synthesise an 'MGS'
            names = ["MGS", name]
        else:
            names = [name]

        for name in names:
            try:
                target_dict = uuid_name_to_target[(blkid_device['uuid'], name)]
                target_dict['devices'].append(dev)
            except KeyError:
                target_dict = {"name": name,
                               "uuid": blkid_device['uuid'],
                               "params": params,
                               "devices": [dev],
                               "mounted": mounted}
                uuid_name_to_target[(blkid_device['uuid'], name)] = target_dict

    return uuid_name_to_target.values()


def get_mgs_targets(local_targets):
    """If there is an MGS in local_targets, use debugfs to
       get a list of targets.  Return a dict of filesystem->(list of targets)"""
    TARGET_NAME_REGEX = "([\w-]+)-(MDT|OST)\w+"
    mgs_target = None
    for t in local_targets:
        if t["name"] == "MGS" and t['mounted']:
            mgs_target = t
    if not mgs_target:
        return ({}, {})

    conf_params = {}
    mgs_targets = {}
    dev = mgs_target["devices"][0]
    ls = shell.try_run(["debugfs", "-c", "-R", "ls -l CONFIGS/", dev])
    filesystems = []
    targets = []
    for line in ls.split("\n"):
        try:
            name = line.split()[8]
            size = line.split()[5]
        except IndexError:
            pass

        if not size:
            continue

        match = re.search("([\w-]+)-client", name)
        if match is not None:
            filesystems.append(match.group(1).__str__())

        match = re.search(TARGET_NAME_REGEX, name)
        if match != None:
            targets.append(match.group(0).__str__())

    def read_log(conf_param_type, conf_param_name, log_name):
        # NB: would use NamedTemporaryFile if we didn't support python 2.4
        from tempfile import mktemp
        tmpfile = mktemp()
        try:
            shell.try_run(["debugfs", "-c", "-R", "dump CONFIGS/%s %s" % (log_name, tmpfile), dev])
            if not os.path.exists(tmpfile):
                # debugfs returns 0 whether it succeeds or not, find out whether
                # dump worked by looking for output file
                return

            if os.path.getsize(tmpfile) == 0:
                # Work around LU-632, wherein an empty config log causes llog_reader to hit
                # an infinite loop.
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

                    mgs_targets[fs_name].append({
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
                    elif re.search(TARGET_NAME_REGEX, object):
                        # Identify target params
                        param_type = 'target'
                        param_name = re.search(TARGET_NAME_REGEX, object).group(0)
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

                    if not param_type in conf_params:
                        conf_params[param_type] = {}
                    if not param_name in conf_params[param_type]:
                        conf_params[param_type][param_name] = {}
                    conf_params[param_type][param_name][key] = val
        finally:
            if os.path.exists(tmpfile):
                os.unlink(tmpfile)

    # Read config log "<fsname>-client" for each filesystem
    for fs in filesystems:
        mgs_targets[fs] = []
        read_log("filesystem", fs, "%s-client" % fs)
        read_log("filesystem", fs, "%s-param" % fs)
        # Don't bother reporting on a FS entry with no targets
        if len(mgs_targets[fs]) == 0:
            del mgs_targets[fs]

    # Read config logs "testfs-MDT0000" etc
    for target in targets:
        read_log("target", target, target)

    return (mgs_targets, conf_params)


def detect_scan():
    local_targets = get_local_targets()
    mgs_targets, mgs_conf_params = get_mgs_targets(local_targets)

    return {"local_targets": local_targets,
        "mgs_targets": mgs_targets,
        "mgs_conf_params": mgs_conf_params}


ACTIONS = [detect_scan]
CAPABILITIES = []
