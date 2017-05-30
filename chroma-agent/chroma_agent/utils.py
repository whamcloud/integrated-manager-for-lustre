# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from collections import defaultdict
import re

from chroma_agent.lib.shell import AgentShell
from chroma_agent.device_plugins.audit.mixins import FileSystemMixin


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
                    device = AgentShell.try_run(['blkid', '-U', uuid]).strip()

                self.fstab.append((device, mntpnt, fstype))
            except ValueError:
                # Empty or malformed line
                pass

    def all(self):
        return self.fstab


class BlkId(dict):
    def __init__(self):
        blkid_lines = AgentShell.try_run(['blkid', '-s', 'UUID', '-s', 'TYPE']).split("\n")

        # Record filesystem type and UUID for each block devices reported by blkid
        for line in [l.strip() for l in blkid_lines if len(l)]:
            # This checks looks for:
            #   /dev/sdX: UUID=<uuid> TYPE=<type>
            # but with UUID and TYPE in either order
            match = re.match("(?P<path>.*): (UUID=\"(?P<uuid>[^\"]*)\"\s*|TYPE=\"(?P<type>[^\"]*)\"\s*)+$", line)
            if match is None:
                # We do not silently drop lines we don't understand, because the BlkId output is
                # important to recognising presence of existing filesystems that we have to warn
                # against overwriting: if we can't read this cleanly, we need to error out rather
                # than risk overwriting something.
                raise RuntimeError("Malformed blkid line '%s'" % line)

            path, uuid, type = match.group("path", "uuid", "type")

            self[path] = {'path': path,
                          'uuid': uuid,
                          'type': type}


def lsof(pid=None, file=None):
    lsof_args = ['lsof', '-F', 'pan0']

    if pid:
        lsof_args += ["-p", str(pid)]

    if file:
        lsof_args += [file]

    pids = defaultdict(dict)
    current_pid = None

    rc, stdout, stderr = AgentShell.run_old(lsof_args)
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
