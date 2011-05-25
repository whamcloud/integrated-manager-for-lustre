#!/usr/bin/env python

import os
import sys
import re
import glob
import simplejson as json
import subprocess

device_lookup = {}
bypath = "/dev/disk/by-path"
for f in os.listdir(bypath):
    device_lookup[os.path.realpath(os.path.join(bypath, f))] = os.path.join(bypath, f)

def normalize_device(device):
    device = device.strip()
    if os.path.commonprefix([bypath, device]) != bypath:
        try:
            return device_lookup[os.path.realpath(device)]
        except KeyError:
            return device
    else:
        return device


def name2kind(name):
    if name == "MGS":
        return "MGS"
    else:
        return re.search("^\\w+-(\\w\\w\\w)", name).group(1)

def audit_info():
    targets = []
    devices_file = "/proc/fs/lustre/devices"
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

            device = normalize_device(open(glob.glob("/proc/fs/lustre/*/%s/mntdev" % name)[0]).read())

            targets.append({
                "running": True,
                "device": device,
                "name": name,
                "uuid": uuid,
                "state": state,
                "kind": name2kind(name),
                "recovery_status": recovery_status,
                })

    running_devices = {}
    for dev in targets:
        running_devices[dev["device"]] = dev

    # Map of filesystem name to mount point and mgs nid
    client_mounts = {}
    def parse_client(dev, mntpnt):
        (nid,fs) = dev.split(":/")
        client_mounts[fs] = {"nid": nid, "mount_point": mntpnt}

    mntpnts = {}
    scan_devices = set()
    for line in open("/etc/fstab").readlines():
        (device, mntpnt, fstype) = line.split()[0:3]
        if not fstype == "lustre":
            continue

        dev = normalize_device(device)
        if re.search(":/", dev):
            try:
                parse_client(device, mntpnt)
                continue
            except:
                print "Bad fstab line '%s'" % line
                sys.exit(-1)

        if dev in running_devices:
            running_devices[dev]["mount_point"] = mntpnt
            continue

        mntpnts[dev] = mntpnt

        scan_devices.add(dev)

    for dev in scan_devices:
        # Skip something that doesn't exist, such as a client mount
        if not os.path.exists(dev):
            continue

        tunefs_text = subprocess.Popen(["tunefs.lustre", dev], stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.read()
        try:
            name = re.search("Target:\\s+(.*)\n", tunefs_text).group(1)
            fs_name = re.search("Lustre FS:\\s+(.*)\n", tunefs_text).group(1)
            targets.append({
                "running": False,
                "kind": name2kind(name),
                "device": dev,
                "name": name,
                "filesystem": fs_name,
                "mount_point": mntpnts[dev]
                })
        except:
            # Failed to get tunefs output, probably not a lustre-formatted
            # volume
            pass

    mount_text = subprocess.Popen(["mount"], stdout=subprocess.PIPE).stdout.read()
    for line in mount_text.split("\n"):
        tokens = line.split()
        try:
            fs = tokens[0].split(":/")[1]
            if client_mounts.has_key(fs):
                client_mounts[fs]["mounted"] = True
        except:
            continue
        
    for (fs, mount) in client_mounts.items():
        if not mount.has_key("mounted"):
            mount["mounted"] = False

    def get_mgs_target(targets):
        for t in targets:
            if t["kind"] == "MGS":
                return  t

    mgs_targets = {}
    mgs_target = get_mgs_target(targets)
    if mgs_target:
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

    lnet_up = os.path.exists("/proc/sys/lnet/stats")
    lnet_nids = []
    if lnet_up:
        lines = open("/proc/sys/lnet/nis").readlines()
        # Skip header line
        for line in lines[1:]:
            tokens = line.split()
            if tokens[0] == "0@lo":
                continue

            lnet_nids.append(tokens[0])

    print json.dumps({"local_targets": targets,
        "mgs_targets": mgs_targets,
        "mgs_pings": mgs_pings,
        "lnet_up": lnet_up,
        "lnet_nids": lnet_nids,
        "client_mounts": client_mounts}, indent=2)

if __name__ == '__main__':
    print json.dumps(audit_info())
