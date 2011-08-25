#!/usr/bin/env python
#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

import os
import sys
import re
import glob
try:
    # Python >= 2.5
    import json
except ImportError:
    # Python 2.4
    import simplejson as json
import subprocess

class LocalLustreAudit:
    def normalize_device(self, device):
        """Try to convert device paths to their /dev/disk/by-path equivalent where possible,
           so that the server can use this is the canonical identifier for devices (it has 
           the best chance of being the same between hosts using shared storage"""

        BY_PATH = "/dev/disk/by-path"

        if not hasattr(self, 'device_lookup'):
            self.device_lookup = {}
            # Lookup devices to their by-path equivalent if possible
            try:
                for f in os.listdir(BY_PATH):
                    self.device_lookup[os.path.realpath(os.path.join(BY_PATH, f))] = os.path.join(BY_PATH, f)
            except OSError:
                # by-path doesn't exist, don't add anything to device_lookup
                pass

            # Resolve the /dev/root node to its real device
            # NB /dev/root may be a symlink on your system, but it's not on all!
            try:
                root = re.search('root=([^ $\n]+)', open('/proc/cmdline').read()).group(1)
                # TODO: resolve UUID= type arguments a la ubuntu
                try:
                    self.device_lookup['/dev/root'] = self.device_lookup[os.path.realpath(root)]
                except KeyError:
                    self.device_lookup['/dev/root'] = root
            except:
                pass

        device = device.strip()
        try:
            return self.device_lookup[os.path.realpath(device)]
        except KeyError:
            pass

        return os.path.realpath(device)

    def name2kind(self, name):
        if name == "MGS":
            return "MGS"
        else:
            return re.search("^\\w+-(\\w\\w\\w)", name).group(1)

    def get_device_nodes(self):
        mount_devices = set([self.normalize_device(i[0]) for i in self.mounts if os.path.exists(i[0])])
        fstab_devices = set([self.normalize_device(i[0]) for i in self.fstab if os.path.exists(i[0])])
        scsi_devices = set([self.normalize_device(path) for path in glob.glob("/dev/disk/by-path/*scsi-*")])
        lvm_devices = set(glob.glob("/dev/mapper/*")) - set(["/dev/mapper/control"])
        virtio_devices = set(glob.glob("/dev/vd*"))
        xen_devices = set(glob.glob("/dev/xvd*"))
        pv_devices = set()
        for line in os.popen("pvs --noheadings -o pv_name").readlines():
            pv_devices.add(line.strip())

        def is_block_device(path):
            from stat import S_ISBLK
            s = os.stat(path)
            return S_ISBLK(s.st_mode)

        def block_device_size(path):
            try:
                fd = os.open(path, os.O_RDONLY)
                try:
                    # os.SEEK_END = 2 (integer required for python 2.4)
                    return os.lseek(fd, 0, 2)
                finally:
                    os.close(fd)
            except:
                return 0
                

        all_devices = mount_devices | fstab_devices | scsi_devices | lvm_devices | virtio_devices | xen_devices
        all_devices = set([d for d in all_devices if is_block_device(d)])

        partitions = {}
        for line in open('/proc/partitions').readlines()[2:]:
            # Store the number of blocks to identify blocks=1 
            # partitions (i.e. extended partitions)
            blocks = int(line.split()[2])
            dev = self.normalize_device("/dev/" + line.split()[3])
            partitions[dev] = blocks

        uuids = {}
        for line in os.popen("blkid %s" % " ".join(all_devices)).readlines():
            match = re.search("^(.+): .*UUID=\"([^\"]+)\"", line)
            if match:
                dev, uuid = match.groups()
                uuid = uuid.replace("-", "")
                assert(len(uuid) == 32)
                uuids[self.normalize_device(dev)] = uuid

        result = []
        for device in all_devices:
            mounted = device in mount_devices
            try:
                uuid = uuids[device]
            except KeyError:
                uuid = ""

            try:
                is_partitioned = (partitions[device + "1"] > 0)
            except KeyError:
                is_partitioned = False

            try:
                extended_partition = (partitions[device] == 1)
            except KeyError:
                extended_partition = False
            used = device in mount_devices or device in fstab_devices or device in pv_devices or extended_partition or is_partitioned

            if device in scsi_devices:
                kind = 'scsi'
            elif device in lvm_devices:
                kind = 'lvm'
            else:
                kind = ''

            result.append({
                'path': device,
                'kind': kind,
                'mounted': mounted,
                'used': used,
                'fs_uuid': uuid,
                'size': block_device_size(device)
                })
        return result

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
                    device = self.normalize_device(open(device_file).read())
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
                for mount_device, mntpnt, fstype in self.mounts:
                    if mount_device == device:
                        mount_point = mntpnt
                    elif self.normalize_device(mount_device) == device:
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
        for device, mntpnt, fstype in self.fstab:
            if not fstype == "lustre":
                continue

            device = self.normalize_device(device)
            if os.path.exists(device):
                device_info[device] = {"mount_point": mntpnt}
                lustre_devices.add(device)

        result = []
        # Interrogate each target that we found in proc or fstab
        for device in lustre_devices:
            tunefs_text = subprocess.Popen(["tunefs.lustre", "--dryrun", device], stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.read()
            try:
                name = re.search("Target:\\s+(.*)\n", tunefs_text).group(1)
                fs_name = re.search("Lustre FS:\\s+([^\n]*)\n", tunefs_text).group(1)
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
                        "filesystem": fs_name,
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

        for device, mntpnt, fstype in self.fstab:
            info = client_info(device, mntpnt, fstype)
            if info:
                client_mounts[mntpnt] = info

        for device, mntpnt, fstype in self.mounts:
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
            # LU-632
            if os.path.getsize(tmpfile) == 0:
                continue
            client_log = subprocess.Popen(["llog_reader", tmpfile], stdout=subprocess.PIPE).stdout.read()

            entries = client_log.split("\n#")[1:]
            fs_targets = []
            for entry in entries:
                tokens = entry.split()
                step_num = tokens[0]
                # ([\w=]+) covers all possible token[0] from
                # lustre/utils/llog_reader.c @ 0f8dca08a4f68cba82c2c822998ecc309d3b7aaf
                (code,action) = re.search("^\\((\d+)\\)([\w=]+)$", tokens[1]).groups()
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

    def read_mounts(self):
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

    def read_fstab(self):
        self.fstab = []
        for line in open("/etc/fstab").readlines():
            line = line.split('#')[0]
            try:
                (device, mntpnt, fstype) = line.split()[0:3]
                self.fstab.append((device, mntpnt, fstype))
            except ValueError:
                # Empty or malformed line
                pass

    def audit_info(self):
        self.read_mounts()
        self.read_fstab()

        local_targets = self.get_local_targets()
        mgs_targets = self.get_mgs_targets(local_targets)
        device_nodes = self.get_device_nodes()
        client_mounts = self.get_client_mounts()
        lnet_loaded, lnet_up, lnet_nids = self.get_lnet_nids()

        # Don't do this in general, it'll be slow with many targets
        #mgs_pings = get_mgs_pings(mgs_targets)
        mgs_pings = {}

        return json.dumps({"local_targets": local_targets,
            "mgs_targets": mgs_targets,
            "mgs_pings": mgs_pings,
            "lnet_loaded": lnet_loaded,
            "lnet_up": lnet_up,
            "lnet_nids": lnet_nids,
            "device_nodes": device_nodes,
            "client_mounts": client_mounts}, indent=2)

if __name__ == '__main__':
    print LocalLustreAudit().audit_info()
