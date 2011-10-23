#!/usr/bin/env python
#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

import os
import sys
import re
import glob
import subprocess
from hydra_agent.audit.local import LocalAudit

def normalize_device(device):
    """Try to convert device paths to their /dev/disk/by-id equivalent where possible,
       so that the server can use this is the canonical identifier for devices (it has 
       the best chance of being the same between hosts using shared storage"""

    # Exceptions where we prefer a symlink to the real node, 
    # to get more human-readable device nodes where possible
    allowed_paths = ["/dev/disk/by-id", "/dev/mapper"]
    if not hasattr(normalize_device, 'device_lookup'):
        normalize_device.device_lookup = {}
        for allowed_path in allowed_paths:
            # Lookup devices to their by-id equivalent if possible
            try:
                for f in os.listdir(allowed_path):
                    normalize_device.device_lookup[os.path.realpath(os.path.join(allowed_path, f))] = os.path.join(allowed_path, f)
            except OSError:
                # Doesn't exist, don't add anything to device_lookup
                pass

        # Resolve the /dev/root node to its real device
        # NB /dev/root may be a symlink on your system, but it's not on all!
        try:
            root = re.search('root=([^ $\n]+)', open('/proc/cmdline').read()).group(1)
            # TODO: resolve UUID= type arguments a la ubuntu
            try:
                normalize_device.device_lookup['/dev/root'] = normalize_device.device_lookup[os.path.realpath(root)]
            except KeyError:
                normalize_device.device_lookup['/dev/root'] = root
        except:
            pass

    device = device.strip()
    try:
        return normalize_device.device_lookup[os.path.realpath(device)]
    except KeyError:
        pass

    return os.path.realpath(device)

class Mounts(object):
    def __init__(self):
        # NB we must use /proc/mounts instead of `mount` because `mount` sometimes
        # reports out of date information from /etc/mtab when a lustre service doesn't
        # tear down properly.
        self.mounts = []
        mount_text = open("/proc/mounts").read()
        for line in mount_text.split("\n"):
            result = re.search("([^ ]+) ([^ ]+) ([^ ]+) ",line)
            if not result:
                continue
            device,mntpnt,fstype = result.groups()

            self.mounts.append((
                device,
                mntpnt,
                fstype))

    def all(self):
        return self.mounts

class Fstab(object):
    def __init__(self):
        self.fstab = []
        for line in open("/etc/fstab").readlines():
            line = line.split('#')[0]
            try:
                (device, mntpnt, fstype) = line.split()[0:3]
                self.fstab.append((device, mntpnt, fstype))
            except ValueError:
                # Empty or malformed line
                pass

    def all(self):
        return self.fstab


class LocalLustreAudit:
    def __init__(self):
        self.mounts = Mounts()
        self.fstab = Fstab()

    def name2kind(self, name):
        if name == "MGS":
            return "MGS"
        else:
            return re.search("^\\w+-(\\w\\w\\w)", name).group(1)

    def get_local_targets(self):
        # List of devices to scan, from /proc and fstab
        lustre_devices = set()

        # Information about running lustre targets learned from /proc
        running_target_info = {}

        # Find running devices in /proc and extract any info that we won't 
        # get from tunefs.lustre later.
        devices_file = "/proc/fs/lustre/devices"
        if os.path.exists(devices_file):
            # NB assume that if proc/fs/lustre/devices exists then 
            # version file will also exist
            version_file = "/proc/fs/lustre/version"
            version_text = open(version_file).read()
            (major, minor, patch) = re.search("lustre: (\\d+).(\\d+).(\\w+)", version_text).groups()
            for line in open(devices_file).readlines():
                # Device names are different in lustre 1.x versus lustre 2.x
                if int(major) < 2:
                    target_types = {"obdfilter": "OST", "mds": "MDT", "mgs": "MGS"}
                else:
                    target_types = {"obdfilter": "OST", "mdt": "MDT", "mgs": "MGS"}

                try:
                    (local_id, state, type, name, uuid, some_other_id) = line.split()
                except ValueError:
                    continue

                if not type in target_types:
                    continue

                recovery_status = {}
                if type != "mgs":
                    try:
                        recovery_file = glob.glob("/proc/fs/lustre/*/%s/recovery_status" % name)[0]
                        recovery_status_text = open(recovery_file).read()
                        for line in recovery_status_text.split("\n"):
                            tokens = line.split(":")
                            if len(tokens) != 2:
                                continue
                            k = tokens[0].strip()
                            v = tokens[1].strip()
                            recovery_status[k] = v
                    except IndexError:
                        # If the recovery_status file doesn't exist,
                        # we will return an empty dict for recovery info
                        pass

                try:
                    device_file = glob.glob("/proc/fs/lustre/*/%s/mntdev" % name)[0]
                    device = normalize_device(open(device_file).read())
                except IndexError:
                    # Oops, the device file went away, probably we're 
                    # scanning something while it's being unmounted
                    continue
                except IOError:
                    # We got as far as finding the device file but couldn't
                    # read it, probably we're scanning something while
                    # it's being unmounted
                    continue

                mount_point = None
                for mount_device, mntpnt, fstype in self.mounts.all():
                    if mount_device == device:
                        mount_point = mntpnt
                    elif normalize_device(mount_device) == device:
                        mount_point = mntpnt

                if not mount_point:
                    # Deal with the situation where a target on its way down
                    # may appear in /proc/fs/lustre but not in /proc/mounts
                    continue

                running_target_info[name] = {"recovery_status": recovery_status, "uuid": uuid, "mount_point": mount_point}
                lustre_devices.add(device)

        # Information about particular devices learned from fstab
        device_info = {}

        # Get all 'lustre' targets from fstab, and merge info with
        # what we learned from /proc or create fresh entries for 
        # targets not previously known
        for device, mntpnt, fstype in self.fstab.all():
            if not fstype == "lustre":
                continue

            device = normalize_device(device)
            if os.path.exists(device):
                device_info[device] = {"mount_point": mntpnt}
                lustre_devices.add(device)

        result = []
        # Interrogate each target that we found in proc or fstab
        for device in lustre_devices:
            tunefs_text = subprocess.Popen(["tunefs.lustre", "--dryrun", device], stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.read()
            try:
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

                running = (name in running_target_info)
                try:
                    mount_point = running_target_info[name]['mount_point']
                except KeyError:
                    mount_point = device_info[device]['mount_point']

                # include/lustre_disk.h
                #define LDD_F_SV_TYPE_MDT   0x0001
                #define LDD_F_SV_TYPE_OST   0x0002
                #define LDD_F_SV_TYPE_MGS   0x0004

                # In the case of a combined MGS+MDT volume, it tunefs reports
                # an MDT name.  We detect that it's also an MGS from the flags,
                # and synthesize an additional name.  The resulting output
                # has two entries, one named "<fsname>-MDTxxxx" and one named
                # "MGS" which refer to the same block device.
                real_names = [name]
                if (flags & 0x0005) == 0x0005:
                    real_names.append("MGS")

                for real_name in real_names:
                    try:
                        recovery_status = running_target_info[real_name]['recovery_status']
                    except:
                        recovery_status = {}

                    result.append({
                        "recovery_status": recovery_status,
                        "mount_point": mount_point,
                        "running": running,
                        "kind": self.name2kind(real_name),
                        "name": real_name,
                        "params": params,
                        "device": device
                        })
            except Exception,e:
                # Failed to get tunefs output, probably not a lustre-formatted
                # volume
                pass

        return result

    def get_client_mounts(self):
        """Parse 'fstab' and 'mount' to get a list of configured clients
           and whether they are mounted.  Return mount point->dict"""
        scan_devices = set()
        client_mounts = {}

        def client_info(device, mntpnt, fstype):
            if fstype == "lustre" and re.search(":/", device) and not os.path.exists(device):
                try:
                    (nid,fs) = device.split(":/")
                except:
                    return None

                return {"filesystem": fs, "nid": nid, "mounted": False}
            else:
                return None

        for device, mntpnt, fstype in self.fstab.all():
            info = client_info(device, mntpnt, fstype)
            if info:
                client_mounts[mntpnt] = info

        for device, mntpnt, fstype in self.mounts.all():
            if mntpnt in client_mounts:
                client_mounts[mntpnt]['mounted'] = True
            else:
                info = client_info(device, mntpnt, fstype)
                if info:
                    info['mounted'] = True
                    client_mounts[mntpnt] = info

        return client_mounts

    def get_mgs_targets(self, local_targets):
        """If there is an MGS in local_targets, use debugfs to 
           get a list of targets.  Return a dict of filesystem->(list of targets)"""
        TARGET_NAME_REGEX = "(\w+)-(MDT|OST)\w+"
        mgs_target = None
        for t in local_targets:
            if t["kind"] == "MGS":
                mgs_target = t
        if not mgs_target:
            return ({}, {})

        conf_params = {}
        mgs_targets = {}
        dev = mgs_target["device"]
        ls = subprocess.Popen(["debugfs", "-c", "-R", "ls -l CONFIGS/", dev], stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.read()
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
                debugfs_rc = subprocess.Popen(["debugfs", "-c", "-R", "dump CONFIGS/%s %s" % (log_name, tmpfile), dev], stdout=subprocess.PIPE, stderr=subprocess.PIPE).wait()
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

    def get_mgs_pings(self, mgs_targets):
        """Attempt to 'lctl ping' all NIDs of targets configured
           in an MGS.  Return a dict of NID->bool (true for 
           successful ping("""
        nids = set()
        for (fs,fs_targets) in mgs_targets.items():
            for t in fs_targets:
                nids.add(t["nid"])

        mgs_pings = {}
        for nid in nids:
            pipe = subprocess.Popen(["lctl", "ping", nid], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            ping_rc = pipe.wait()
            if ping_rc == 0:
                ping = True
            else:
                ping = False
            mgs_pings[nid] = ping

        return mgs_pings

    def get_lnet_nids(self):
        """Parse /proc for running LNet NIDs, and return a 2-tuple of 
           (whether lnet is up, list of NID strings)"""
        lnet_nids = []

        lnet_loaded = False
        for module_line in open("/proc/modules").readlines():
            if module_line.startswith("lnet "):
                lnet_loaded = True
                break

        lnet_up = os.path.exists("/proc/sys/lnet/stats")
        if lnet_up:
            lines = open("/proc/sys/lnet/nis").readlines()
            # Skip header line
            for line in lines[1:]:
                tokens = line.split()
                if tokens[0] != "0@lo":
                    lnet_nids.append(tokens[0])

        return lnet_loaded, lnet_up, lnet_nids

    def audit_info(self):
        local_targets = self.get_local_targets()
        mgs_targets, mgs_conf_params = self.get_mgs_targets(local_targets)
        client_mounts = self.get_client_mounts()
        lnet_loaded, lnet_up, lnet_nids = self.get_lnet_nids()

        # Don't do this in general, it'll be slow with many targets
        #mgs_pings = get_mgs_pings(mgs_targets)
        mgs_pings = {}

        audit = LocalAudit()

        from hydra_agent.actions.targets import get_resource_locations

        return {"local_targets": local_targets,
            "mgs_targets": mgs_targets,
            "mgs_conf_params": mgs_conf_params,
            "mgs_pings": mgs_pings,
            "lnet_loaded": lnet_loaded,
            "lnet_up": lnet_up,
            "lnet_nids": lnet_nids,
            "client_mounts": client_mounts,
            "resource_locations": get_resource_locations(),
            "metrics": audit.metrics()}

if __name__ == '__main__':
    print LocalLustreAudit().audit_info()
