#!/usr/bin/env python

import os
import sys
import re
import glob
import simplejson as json
import subprocess

class LocalLustreAudit:
    def normalize_device(self, device):
        bypath = "/dev/disk/by-path"
        if not hasattr(self, 'device_lookup'):
            self.device_lookup = {}
            for f in os.listdir(bypath):
                self.device_lookup[os.path.realpath(os.path.join(bypath, f))] = os.path.join(bypath, f)


        device = device.strip()
        if os.path.commonprefix([bypath, device]) != bypath:
            try:
                return self.device_lookup[os.path.realpath(device)]
            except KeyError:
                return device
        else:
            return device


    def name2kind(self, name):
        if name == "MGS":
            return "MGS"
        else:
            return re.search("^\\w+-(\\w\\w\\w)", name).group(1)

    def get_local_targets(self):
        devices_file = "/proc/fs/lustre/devices"
        targets = {}
        # Find running devices in /proc and extract any info that we won't 
        # get from tunefs.lustre later.
        if os.path.exists(devices_file):
            for line in open(devices_file).readlines():
                target_types = {"obdfilter": "OST", "mdt": "MDT", "mgs": "MGS"}
                try:
                    (local_id, state, type, name, uuid, some_other_id) = line.split()
                except ValueError:
                    continue

                if not type in target_types:
                    continue

                recovery_status = {}
                if type != "mgs":
                    recovery_file = glob.glob("/proc/fs/lustre/*/%s/recovery_status" % name)[0]
                    recovery_status_text = open(recovery_file).read()
                    for line in recovery_status_text.split("\n"):
                        tokens = line.split(":")
                        if len(tokens) != 2:
                            continue
                        k = tokens[0].strip()
                        v = tokens[1].strip()
                        recovery_status[k] = v

                device = self.normalize_device(open(glob.glob("/proc/fs/lustre/*/%s/mntdev" % name)[0]).read())

                targets[device] = {"recovery_status": recovery_status, "uuid": uuid, "running": True}

        mntpnts = {}

        # Get all 'lustre' targets from fstab, and merge info with
        # what we learned from /proc or create fresh entries for 
        # targets not previously known
        for line in open("/etc/fstab").readlines():
            (device, mntpnt, fstype) = line.split()[0:3]
            if not fstype == "lustre":
                continue

            device = self.normalize_device(device)
            if os.path.exists(device):
                info = {"mount_point": mntpnt, "recovery_status": {}}
                if targets.has_key(device):
                    targets[device] = dict(targets[device].items() + info.items())
                else:
                    targets[device] = info
            else:
                # TODO: log warning that we found a device that doesn't exist unless
                # it's a client-looking 'device'
                pass

        # Interrogate each target that we found in proc or fstab
        for device,device_info in targets.items():
            tunefs_text = subprocess.Popen(["tunefs.lustre", "--dryrun", device], stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.read()
            try:
                name = re.search("Target:\\s+(.*)\n", tunefs_text).group(1)
                fs_name = re.search("Lustre FS:\\s+([^\n]*)\n", tunefs_text).group(1)
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

                # If no 'running' set for the device before, then it wasn't
                # interrogated from /proc and is therefore not running
                if device_info.has_key('running'):
                    running = device_info['running']
                else:
                    running = False

                targets[device] = dict(targets[device].items() + {
                    "running": running,
                    "kind": self.name2kind(name),
                    "name": name,
                    "filesystem": fs_name,
                    "params": params,
                    "device": device
                    }.items())
            except Exception,e:
                del targets[device]
                # Failed to get tunefs output, probably not a lustre-formatted
                # volume
                pass

        return targets.values()

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

        for line in open("/etc/fstab").readlines():
            (device, mntpnt, fstype) = line.split()[0:3]
            info = client_info(device, mntpnt, fstype)
            if info:
                client_mounts[mntpnt] = info

        # NB we must use /proc/mounts instead of `mount` because `mount` sometimes
        # reports out of date information from /etc/mtab when a lustre service doesn't
        # tear down properly.
        mount_text = open("/proc/mounts").read()
        for line in mount_text.split("\n"):
            result = re.search("([^ ]+) ([^ ]+) ([^ ]+) ",line)
            if not result:
                continue

            device,mntpnt,fstype = result.groups()
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
        mgs_target = None
        for t in local_targets:
            if t["kind"] == "MGS":
                mgs_target = t
        if not mgs_target:
            return {}

        mgs_targets = {}
        dev = mgs_target["device"]
        ls = subprocess.Popen(["debugfs", "-c", "-R", "ls -l CONFIGS/", dev], stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.read()
        filesystems = []
        for line in ls.split("\n"):
            try:
                name = line.split()[8]
            except IndexError:
                pass
            match = re.search("(\w+)-client", name)
            if match != None:
                filesystems.append(match.group(1).__str__())

        for fs in filesystems:
            tmpfile = "/tmp/debugfs.tmp"
            debugfs_rc = subprocess.Popen(["debugfs", "-c", "-R", "dump CONFIGS/%s-client %s" % (fs, tmpfile), dev], stdout=subprocess.PIPE, stderr=subprocess.PIPE).wait()
            client_log = subprocess.Popen(["llog_reader", tmpfile], stdout=subprocess.PIPE).stdout.read()

            entries = client_log.split("\n#")[1:]
            fs_targets = []
            for entry in entries:
                tokens = entry.split()
                step_num = tokens[0]
                (code,action) = re.search("^\\((\d+)\\)(\w+)$", tokens[1]).groups()
                if action == 'setup':
                    volume = re.search("0:(\w+-\w+)-\w+", tokens[2]).group(1)
                    uuid = re.search("1:(.*)", tokens[3]).group(1)
                    nid = re.search("2:(.*)", tokens[4]).group(1)

                    fs_targets.append({
                        "uuid": uuid,
                        "name": volume,
                        "nid": nid})

            mgs_targets[fs] = fs_targets

        return mgs_targets

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
        lnet_up = os.path.exists("/proc/sys/lnet/stats")
        if lnet_up:
            lines = open("/proc/sys/lnet/nis").readlines()
            # Skip header line
            for line in lines[1:]:
                tokens = line.split()
                if tokens[0] != "0@lo":
                    lnet_nids.append(tokens[0])

        return lnet_up, lnet_nids

    def audit_info(self):
        local_targets = self.get_local_targets()
        mgs_targets = self.get_mgs_targets(local_targets)
        client_mounts = self.get_client_mounts()
        lnet_up, lnet_nids = self.get_lnet_nids()

        # Don't do this in general, it'll be slow with many targets
        #mgs_pings = get_mgs_pings(mgs_targets)
        mgs_pings = {}

        return json.dumps({"local_targets": local_targets,
            "mgs_targets": mgs_targets,
            "mgs_pings": mgs_pings,
            "lnet_up": lnet_up,
            "lnet_nids": lnet_nids,
            "client_mounts": client_mounts}, indent=2)

if __name__ == '__main__':
    print LocalLustreAudit().audit_info()
