# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================


from hydra_agent.plugins import DevicePlugin

from hydra_agent.log import agent_log
from hydra_agent import shell
from hydra_agent.plugins import ActionPlugin

#from hydra_agent.plugins import DevicePluginManager

import os
import glob
import re


class LinuxDevicePlugin(DevicePlugin):
    def start_session(self):
        return device_scan()

    def update_session(self):
        pass


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
        rc, out, err = shell.run([SCSI_ID_PATH, '--version'])
        old_udev = (rc != 0)

    # Note: the -p 0x80 scsi_id is good for getting
    # a textual id along the lines of:
    # * SQEMU    QEMU HARDDISK  WD-deadbeef0
    # * SOPNFILERVIRTUAL-DISK   9iI2mH-4Ddf-k3Ov
    # * SDDN     S2A 9550       058C4A531100
    # As well as being more readable than the 0x83 ID, this
    # gets us the serial number for QEMU devices if the user
    # has set one, whereas that doesn't show up in 0x83.

    def scsi_id_command(cmd):
        rc, out, err = shell.run(cmd)
        if rc != 0:
            return None
        else:
            return out.strip()

    if old_udev:
        # Old scsi_id, operates on a /sys reference
        serial_80 = scsi_id_command(["scsi_id", "-g", "-p", "0x80", "-s", "/block/%s" % device_name])
        serial_83 = scsi_id_command(["scsi_id", "-g", "-p", "0x83", "-s", "/block/%s" % device_name])
    else:
        # New scsi_id, always operates directly on a device
        serial_80 = scsi_id_command(["scsi_id", "-g", "-p", "0x80", path])
        serial_83 = scsi_id_command(["scsi_id", "-g", "-p", "0x83", path])

    # The downside to using -p 0x80 is that if the user hasn't manually
    # set serials for their scsi devices, multiple different devices on
    # the same host return the same string, so we need an explicit
    # exclusion for that
    if serial_80 == "SQEMU    QEMU HARDDISK  0":
        serial_80 = None
    if serial_83 and serial_83.find("0QEMU    QEMU HARDDISK") == 0:
        serial_83 = None

    info = {'major_minor': major_minor,
            'path': path,
            'serial_80': serial_80,
            'serial_83': serial_83,
            'size': size,
            'parent': parent}

    return info


def _parse_sys_block():
    mapper_devs = _find_block_devs("/dev/mapper/")
    by_id_nodes = _find_block_devs("/dev/disk/by-id/")
    by_path_nodes = _find_block_devs("/dev/disk/by-path/")

    def get_path(major_minor, device_name):
        # Try to find device nodes for these:
        fallback_dev_path = os.path.join("/dev/", device_name)
        # * First look in /dev/mapper
        if major_minor in mapper_devs:
            return mapper_devs[major_minor]
        # * Then try /dev/disk/by-id
        elif major_minor in by_id_nodes:
            return by_id_nodes[major_minor]
        # * Then try /dev/disk/by-path
        elif major_minor in by_path_nodes:
            return by_path_nodes[major_minor]
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

        # Exclude ramdisks, floppy drives, obvious cdroms
        if re.search("^ram\d+$", device_name) or \
           re.search("^fd\d+$", device_name) or \
           re.search("^sr\d+$", device_name):
            return

        # Exclude read-only or removed devices
        try:
            open("/dev/%s" % device_name, 'w')
        except IOError, e:
            import errno
            # Python errno doesn't include this code
            NO_MEDIA_ERRNO = 123
            if e.errno == errno.EROFS or e.errno == NO_MEDIA_ERRNO:
                return

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


def _get_md():
    try:
        matches = re.finditer("^(md\d+) :", open('/proc/mdstat', 'r').read().strip(), flags = re.MULTILINE)
        devs = []
        for match in matches:
            # e.g. md0
            device_name = match.group(1)
            device_path = "/dev/%s" % device_name
            detail = shell.try_run(['mdadm', '--brief', '--detail', '--verbose', device_path])
            device_uuid = re.search("UUID=(.*)[ \\n]", detail.strip(), flags = re.MULTILINE).group(1)
            device_list_csv = re.search("^   devices=(.*)$", detail.strip(), flags = re.MULTILINE).group(1)
            device_list = device_list_csv.split(",")

            devs.append({
                "uuid": device_uuid,
                "path": device_path,
                "device_paths": device_list
                })
        return devs
    except IOError:
        return []


def device_scan(args = None):
    # Map of block devices major:minors to /dev/ path.
    block_device_nodes, node_block_devices = _parse_sys_block()

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
        dm_type = tokens[3]

        node_path = os.path.join("/dev/mapper", name)
        block_device = node_block_devices[node_path]

        if dm_type in ['linear', 'striped']:
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

            # Try to get information about LVs from this VG which we queried
            # earlier with _get_vg/_get_lv.  This can fail if the system is in an in-between
            # state where it still has device nodes for some LVs which are
            # no longer really there
            try:
                vg_lv_info = lvs[vg_name]
            except KeyError:
                continue

            if not lv_name in vg_lv_info:
                # This isn't something we saw as a named LV, so its
                # a partition.  Assign its parent and don't store it
                # as an LV.
                result = re.search("(.*)p\d+", lv_name)
                if not result:
                    agent_log.error("Cannot parse LVM device name %s" % name)
                    continue
                parent_lv_name = result.groups()[0]
                if not parent_lv_name in lvs[vg_name]:
                    agent_log.error("Cannot parse LVM device name %s" % name)
                else:
                    # HYD-744: FIXME: compose path in a way that copes with hyphens
                    parent_block_device = node_block_devices["/dev/mapper/%s-%s" % (vg_name, parent_lv_name)]
                    block_device_nodes[block_device]['parent'] = parent_block_device

                continue
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

    mds = {}
    for md in _get_md():
        path = md['path']
        block_device = node_block_devices[md['path']]
        uuid = md['uuid']
        device_paths = md['device_paths']
        drives = [_dev_major_minor(dp) for dp in device_paths]
        mds[uuid] = {'path': path, 'block_device': block_device, 'drives': drives}

    # Anything in fstab or that is mounted
    from hydra_agent.utils import Fstab, Mounts
    fstab = Fstab()
    mounts = Mounts()
    from itertools import chain
    bdev_to_local_fs = {}
    for dev, mntpnt, fstype in chain(fstab.all(), mounts.all()):
        mm = _dev_major_minor(dev)
        if mm and fstype != 'lustre' and mm in block_device_nodes:
            bdev_to_local_fs[mm] = (mntpnt, fstype)

    return {"vgs": vgs,
            "lvs": lvs,
            "mpath": mpaths,
            "devs": block_device_nodes,
            "local_fs": bdev_to_local_fs,
            'mds': mds}


class DeviceScanPlugin(ActionPlugin):
    def register_commands(self, parser):
        p = parser.add_parser("device-scan",
                              help="scan for devices, or something")
        p.set_defaults(func=device_scan)
