# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

import os
import re


def normalize_device(device):
    """Try to convert device paths to their /dev/disk/by-id equivalent where
        possible, so that the server can use this is the canonical identifier
        for devices (it has the best chance of being the same between hosts
        using shared storage"""

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
            result = re.search("([^ ]+) ([^ ]+) ([^ ]+) ", line)
            if not result:
                continue
            device, mntpnt, fstype = result.groups()

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
