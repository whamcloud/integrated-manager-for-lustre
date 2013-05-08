#
# INTEL CONFIDENTIAL
#
# Copyright 2013 Intel Corporation All Rights Reserved.
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


from chroma_agent import shell

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


class BlkId(object):
    def __init__(self):
        blkid_lines = shell.try_run(['blkid', '-s', 'UUID', '-s', 'TYPE']).split("\n")

        # Record filesystem type and UUID for each block devices reported by blkid
        devices = []
        for line in [l.strip() for l in blkid_lines if len(l)]:
            match = re.match("(.*): UUID=\"([^\"]*)\" TYPE=\"([^\"]*)\"$", line)
            if match is None:
                # BlkId only reports devices that contain a filesystem (will have a TYPE), but
                # not all filesystems have a UUID (e.g. iso9660 doesn't).
                match = re.match("(.*): TYPE=\"([^\"]*)\"$", line)
                if match:
                    path, type = match.groups()
                    uuid = None
                else:
                    # We do not silently drop lines we don't understand, because the BlkId output is
                    # important to recognising presence of existing filesystems that we have to warn
                    # against overwriting: if we can't read this cleanly, we need to error out rather
                    # than risk overwriting something.
                    raise RuntimeError("Malformed blkid line '%s'" % line)
            else:
                path, uuid, type = match.groups()

            devices.append({
                'path': path,
                'uuid': uuid,
                'type': type
            })
        self.devices = devices

    def all(self):
        return self.devices
