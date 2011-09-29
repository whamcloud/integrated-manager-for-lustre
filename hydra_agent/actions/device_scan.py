#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from hydra_agent.log import agent_log
from hydra_agent import shell

import os
import glob
import re

def _dev_major_minor(path):
    """Return a string if 'path' is a block device or link to one, else return None"""
    from stat import S_ISBLK
    try:
        s = os.stat(path)
    except OSError:
        return None

    if S_ISBLK(s.st_mode):
        return "%d:%d" % (os.major(s.st_rdev), os.minor(s.st_rdev))
    else:
        return None

def _find_block_devs(folder):
    # Map of major_minor to path
    result = {}
    for path in glob.glob(os.path.join(folder, "*")):
        mm = _dev_major_minor(path)
        if mm:
            result[mm] = path

    return result

def _get_vgs():
    out = shell.try_run(["vgs", "--units", "b", "--noheadings", "-o", "vg_name,vg_uuid,vg_size"])

    lines = [l for l in out.split("\n") if len(l) > 0]
    for line in lines:
        name, uuid, size_str = line.split()
        size = int(size_str[0:-1], 10)
        yield (name, uuid, size)

def _get_lvs(vg_name):
    out = shell.try_run(["lvs", "--units", "b", "--noheadings", "-o", "lv_name,lv_uuid,lv_size,lv_path", vg_name])

    lines = [l for l in out.split("\n") if len(l) > 0]
    for line in lines:
        name, uuid, size_str, path = line.split()
        size = int(size_str[0:-1], 10)
        yield (name, uuid, size, path)

old_udev = None
def _device_node(device_name, major_minor, path, size, parent):
    # This is a WTF, when I declare old_udev at module scope this function can't see it?!?!
    global old_udev
    # Old (RHEL5) version of scsi_id has a different command line
    # syntax to new (RHEL6) version.  Tell them apart with --version
    # (old one doesn't have --version, new one does)
    SCSI_ID_PATH = "/sbin/scsi_id"
    if old_udev == None:
        rc, out, err = shell.run(['scsi_id', '--version'])
        old_udev = (rc != 0)

    if old_udev:
        # Old scsi_id, operates on a /sys reference
        rc, out, err = shell.run(["scsi_id", "-g", "-s", "/block/%s" % device_name])
        if rc != 0:
            serial = None
        else:
            serial = out.strip()
    else:
        # New scsi_id, always operates directly on a device
        rc, out, err = shell.run(["scsi_id", "-g", path])
        if rc != 0:
            serial = None
        else:
            serial = out.strip()

    return {'major_minor': major_minor,
            'path': path,
            'serial': serial,
            'size': size,
            'parent': parent}

def _parse_sys_block():
    mapper_devs = _find_block_devs("/dev/mapper/")
    by_id_devs = _find_block_devs("/dev/disk/by-id/")

    def get_path(major_minor, device_name):
        # Try to find device nodes for these:
        fallback_dev_path = os.path.join("/dev/", device_name)
        # * First look in /dev/mapper
        if major_minor in mapper_devs:
            return mapper_devs[major_minor]
        # * Then try /dev/disk/by-id
        elif major_minor in by_id_devs:
            return by_id_devs[major_minor]
        # * Then fall back to just /dev
        elif os.path.exists(fallback_dev_path):
            return fallback_dev_path
        else:
            agent_log.warning("Could not find device node for %s (%s)" % (major_minor, fallback_dev_path))
            return None

    block_device_nodes = {}
    node_block_devices = {}

    def parse_block_dir(dev_dir, parent = None):
        """Parse a dir like /sys/block/sda (must contain 'dev' and 'size')"""
        device_name = dev_dir.split(os.sep)[-1]
        major_minor = open(os.path.join(dev_dir, "dev")).read().strip()
        size = int(open(os.path.join(dev_dir, "size")).read().strip()) * 512

        # Exclude zero-sized devices
        if size == 0:
            return

        # Exclude ramdisks and floppy drives
        if re.search("^ram\d+$", device_name) or \
           re.search("^fd\d+$", device_name) or \
           re.search("^sr\d+$", device_name):
            return

        # TODO: more general check for read-only devices in addition to 'sr\d' check above

        # Resolve a major:minor to a /dev/foo
        path = get_path(major_minor, device_name)
        if path:
            block_device_nodes[major_minor] = _device_node(device_name, major_minor, path, size, parent)
            node_block_devices[path] = major_minor

        return major_minor

    for dev_dir in glob.glob("/sys/block/*"):
        major_minor = parse_block_dir(dev_dir)

        partitions = glob.glob(os.path.join(dev_dir, "*/dev"))
        for p in partitions:
            parse_block_dir(os.path.split(p)[0], parent = major_minor)

    return block_device_nodes, node_block_devices

def device_scan(args):
    # Map of block devices major:minors to /dev/ path.
    block_device_nodes, node_block_devices = _parse_sys_block()

    # XXX
    # because it's a pain, and rare, we're not handling "partitions in LVs".
    # normal partitions are fine because they appear as subdirs of the device
    # in /sys/block, but for some reason partitions in LVs don't do that.

    vgs = {}
    lvs = {}
    for vg_name, vg_uuid, vg_size in _get_vgs():
        vgs[vg_name] = {
                'name': vg_name,
                'uuid': vg_uuid,
                'size': vg_size,
                'pvs_major_minor': []}
        lvs[vg_name] = {}
        for lv_name, lv_uuid, lv_size, lv_path in _get_lvs(vg_name):
            lvs[vg_name][lv_name] = {
                'name': lv_name,
                'uuid': lv_uuid,
                'size': lv_size}

    # Map multipath name to set of devices
    mpaths = {}

    stdout = shell.try_run(['dmsetup', 'table'])
    if stdout.strip() == "No devices found":
        dm_lines = []
    else:
        dm_lines = [i for i in stdout.split("\n") if len(i) > 0]
    for line in dm_lines:
        tokens = line.split()
        name = tokens[0].strip(":")
        num_sectors = int(tokens[2])
        dm_type = tokens[3]
        node_class = None

        node_path = os.path.join("/dev/mapper", name)
        block_device = node_block_devices[node_path]

        if dm_type in ['linear', 'striped']:
            obj_class = 'lv'
            # This is an LVM LV
            if dm_type == 'striped':
                # List of striped devices
                dev_indices = range(6, len(tokens), 2)
                devices = [tokens[i] for i in dev_indices]
            elif dm_type == 'linear':
                # Single device linear range
                devices = [tokens[4]]

            # When a name has a "-" in it, DM prints a double hyphen in the output
            # So for an LV called "my-lv" you get VolGroup00-my--lv
            vg_name, lv_name = re.search("(.*[^-])-([^-].*)", name).groups()
            vg_name = vg_name.replace("--", "-")
            lv_name = lv_name.replace("--", "-")

            lvs[vg_name][lv_name]['block_device'] = block_device

            devices = [block_device_nodes[i]['major_minor'] for i in devices]
            vgs[vg_name]['pvs_major_minor'] = list(set(vgs[vg_name]['pvs_major_minor']) | set(devices))
        elif dm_type == 'multipath':
            # This is a multipath device, there will be a list of devices like this:
            # "round-robin 0 1 1 8:80 1000"
            dev_indices = range(12, len(tokens), 6)
            devices = [tokens[i] for i in dev_indices]
            devices = [block_device_nodes[i] for i in devices]
            if name in mpaths:
                raise RuntimeError("Duplicated mpath device %s" % name)

            mpaths[name] = {
                    "name": name,
                    "block_device": block_device,
                    "nodes": devices
                    }
        else:
            continue

    # Anything in fstab or that is mounted
    # TODO: move these out somewhere
    from hydra_agent.legacy_audit import Fstab, Mounts
    fstab = Fstab()
    mounts = Mounts()
    from itertools import chain
    bdev_to_local_fs = {}
    for dev, mntpnt, fstype in chain(fstab.all(), mounts.all()):
        mm = _dev_major_minor(dev)
        if mm and fstype != 'lustre' and mm in block_device_nodes:
            bdev_to_local_fs[mm] = (mntpnt, fstype)

    return {"vgs": vgs, "lvs": lvs, "mpath": mpaths, "devs": block_device_nodes, "local_fs": bdev_to_local_fs}
