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
from chroma_agent.device_plugins.audit.mixins import FileSystemMixin

from collections import defaultdict
import os
import re
import glob


def normalize_device(device):
    from chroma_agent.device_plugins.linux import DeviceHelper
    _d = normalize_device._devices = getattr(normalize_device, '_devices', {})

    d_majmin = DeviceHelper()._dev_major_minor(device)
    u_device = os.path.realpath(device)
    if not _d or u_device not in _d or d_majmin != DeviceHelper()._dev_major_minor(_d[u_device]):
        lookup_paths = ["/dev/disk/by-id/*", "/dev/mapper/*"]

        for p in lookup_paths:
            for f in glob.glob(p):
                _d[os.path.realpath(f)] = f

        root = re.search('root=([^ $\n]+)', open('/proc/cmdline').read()).group(1)
        if '/dev/root' not in _d and os.path.exists(root):
            _d['/dev/root'] = root

    return _d.get(u_device, u_device)


class Mounts(FileSystemMixin):
    def __init__(self):
        # NB we must use /proc/mounts instead of `mount` because `mount` sometimes
        # reports out of date information from /etc/mtab when a lustre service doesn't
        # tear down properly.
        self.mounts = []
        for line in self.read_lines("/proc/mounts"):
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

                uuid_match = re.match("UUID=([\w-]+)$", device)
                if uuid_match:
                    # Resolve UUID to device node path
                    uuid = uuid_match.group(1)
                    device = shell.try_run(['blkid', '-U', uuid]).strip()

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


def lsof(pid=None, file=None):
    lsof_args = ['lsof', '-F', 'pan0']

    if pid:
        lsof_args += ["-p", str(pid)]

    if file:
        lsof_args += [file]

    pids = defaultdict(dict)
    current_pid = None

    rc, stdout, stderr = shell.run(lsof_args)
    if rc != 0:
        if stderr:
            raise RuntimeError(stderr)
        # lsof exits non-zero if there's nothing holding the file open
        return pids

    for line in stdout.split("\n"):
        match = re.match(r'^p(\d+)\x00', line)
        if match:
            current_pid = match.group(1)
            continue

        match = re.match(r'^a(\w)\x00n(.*)\x00', line)
        if match:
            mode = match.group(1)
            file = match.group(2)
            pids[current_pid][file] = {'mode': mode}

    return pids
