
def detect_scan(args):
    pass

import os
import sys
import re
import glob
import subprocess

from hydra_agent.legacy_audit import normalize_device, Mounts, Fstab
from hydra_agent import shell
    
def get_local_targets():
    blkid_lines = shell.try_run(['blkid', '-s', 'UUID']).split("\n")

    lustre_devices = []

    for line in [l for l in blkid_lines if len(l)]:
        dev, uuid = re.search("(.*): UUID=\"(.*)\"", line).groups()
        dev = normalize_device(dev)

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
            for param,value in [t.split('=') for t in params_re.group(1).split()]:
                if not params.has_key(param):
                    params[param] = []
                params[param].append(value)
        else:
            params = {}

        if name.find("ffff") != -1:
            # Do not report unregistered lustre targets
            continue

        mounted = dev in set([normalize_device(m[0]) for m in Mounts().all()])

        lustre_devices.append({
            "name": name,
            "uuid": uuid,
            "params": params,
            "device": dev,
            "mounted": mounted
            })
        if flags & 0x0005 == 0x0005:
            # For combined MGS/MDT volumes, synthesise an 'MGS'
            lustre_devices.append({
                "name": "MGS",
                "uuid": uuid,
                "params": params,
                "device": dev,
                "primary_nid": primary_nid,
                "mounted": mounted
                })

    return lustre_devices

def get_mgs_targets(local_targets):
    """If there is an MGS in local_targets, use debugfs to 
       get a list of targets.  Return a dict of filesystem->(list of targets)"""
    TARGET_NAME_REGEX = "(\w+)-(MDT|OST)\w+"
    mgs_target = None
    for t in local_targets:
        if t["name"] == "MGS":
            mgs_target = t
    if not mgs_target:
        return ({}, {})

    conf_params = {}
    mgs_targets = {}
    dev = mgs_target["device"]
    ls = shell.try_run(["debugfs", "-c", "-R", "ls -l CONFIGS/", dev])
    filesystems = []
    targets = []
    for line in ls.split("\n"):
        try:
            name = line.split()[8]
            size = line.split()[5]
        except IndexError:
            pass

        if size == 0:
            continue

        match = re.search("(\w+)-client", name)
        if match != None:
            filesystems.append(match.group(1).__str__())

        match = re.search(TARGET_NAME_REGEX, name)
        if match != None:
            targets.append(match.group(0).__str__())

    def read_log(conf_param_type, conf_param_name, log_name):
        # NB: would use NamedTemporaryFile if we didn't support python 2.4
        from tempfile import mktemp
        tmpfile = mktemp()
        try:
            debugfs_rc = shell.try_run(["debugfs", "-c", "-R", "dump CONFIGS/%s %s" % (log_name, tmpfile), dev])
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
                step_num = tokens[0]
                # ([\w=]+) covers all possible token[0] from
                # lustre/utils/llog_reader.c @ 0f8dca08a4f68cba82c2c822998ecc309d3b7aaf
                (code,action) = re.search("^\\((\d+)\\)([\w=]+)$", tokens[1]).groups()
                if conf_param_type == 'filesystem' and action == 'setup':
                    # e.g. entry="#09 (144)setup     0:flintfs-MDT0000-mdc  1:flintfs-MDT0000_UUID  2:192.168.122.105@tcp"
                    volume = re.search("0:(\w+-\w+)-\w+", tokens[2]).group(1)
                    fs_name = volume.split("-")[0]
                    uuid = re.search("1:(.*)", tokens[3]).group(1)
                    nid = re.search("2:(.*)", tokens[4]).group(1)

                    mgs_targets[fs_name].append({
                        "uuid": uuid,
                        "name": volume,
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

                    if not conf_params.has_key(param_type):
                        conf_params[param_type] = {}
                    if not conf_params[param_type].has_key(param_name):
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

    # Read config logs "testfs-MDT0000" etc
    for target in targets:
        read_log("target", target, target)


    return (mgs_targets, conf_params)

def detect_scan(args):
    local_targets = get_local_targets()
    mgs_targets, mgs_conf_params = get_mgs_targets(local_targets)

    return {"local_targets": local_targets,
        "mgs_targets": mgs_targets,
        "mgs_conf_params": mgs_conf_params}
