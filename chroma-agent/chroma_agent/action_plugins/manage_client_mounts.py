# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import os
import errno

from chroma_agent.lib.shell import AgentShell


FSTAB_ENTRY_TEMPLATE = "%s\t%s\t\tlustre\tdefaults,_netdev\t0 0\n"


def delete_fstab_entry(mountspec, *unused):
    old_path = "/etc/fstab"
    new_path = "/etc/fstab.iml.edit"
    new_lines = []

    needs_update = False
    with open(old_path, "r") as old:
        for line in old:
            if len(line) > 1 and mountspec == line.split()[0]:
                needs_update = True
            else:
                new_lines.append(line)

    if needs_update:
        with open(new_path, "w") as new:
            for line in new_lines:
                new.write(line)
        os.rename(new_path, old_path)


def create_fstab_entry(mountspec, mountpoint):
    # Ensure that we're not appending this twice
    delete_fstab_entry(mountspec, mountpoint)

    with open("/etc/fstab", "a") as f:
        f.write(FSTAB_ENTRY_TEMPLATE % (mountspec, mountpoint))


def mount_lustre_filesystem(mountspec, mountpoint):
    try:
        os.makedirs(mountpoint, 0755)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

    create_fstab_entry(mountspec, mountpoint)
    AgentShell.try_run(['/bin/mount', mountpoint])


def mount_lustre_filesystems(filesystems):
    for mountspec, mountpoint in filesystems:
        mount_lustre_filesystem(mountspec, mountpoint)


def unmount_lustre_filesystem(mountspec, mountpoint):
    delete_fstab_entry(mountspec, mountpoint)
    AgentShell.try_run(['/bin/umount', mountpoint])


def unmount_lustre_filesystems(filesystems):
    for mountspec, mountpoint in filesystems:
        unmount_lustre_filesystem(mountspec, mountpoint)


ACTIONS = [mount_lustre_filesystems, unmount_lustre_filesystems, mount_lustre_filesystem, unmount_lustre_filesystem]
CAPABILITIES = ['manage_client_mounts']
