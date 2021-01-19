// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use device_types::mount::{Mount, MountCommand};
use im::HashSet;

/// Mutably updates the Mount portion of the device map in response to `MountCommand`s.
pub fn update_mount<S: ::std::hash::BuildHasher>(
    mut local_mounts: HashSet<Mount, S>,
    cmd: MountCommand,
) -> HashSet<Mount, S> {
    match cmd {
        MountCommand::AddMount(target, source, fstype, opts) => {
            local_mounts.update(Mount::new(target, source, fstype, opts))
        }
        MountCommand::RemoveMount(target, source, fstype, opts) => {
            local_mounts.without(&Mount::new(target, source, fstype, opts))
        }
        MountCommand::ReplaceMount(target, source, fstype, opts, old_ops) => {
            let mount = Mount::new(target, source, fstype, old_ops);

            local_mounts.remove(&mount);

            local_mounts.update(Mount { opts, ..mount })
        }
        MountCommand::MoveMount(target, source, fstype, opts, old_target) => {
            let mount = Mount::new(old_target, source, fstype, opts);

            local_mounts.remove(&mount);

            local_mounts.update(Mount { target, ..mount })
        }
    }
}

#[cfg(test)]
mod tests {
    use super::update_mount;
    use device_types::{
        mount::{FsType, Mount, MountCommand, MountOpts, MountPoint},
        DevicePath,
    };
    use im::hashset;
    use insta::assert_debug_snapshot;

    #[test]
    fn test_mount_update() {
        let mounts: im::HashSet<device_types::mount::Mount> = hashset!();

        let add_cmd = MountCommand::AddMount(
            MountPoint("/mnt/part1".into()),
            DevicePath("/dev/sde1".into()),
            FsType("ext4".to_string()),
            MountOpts("rw,relatime,data=ordered".to_string()),
        );

        let mounts = update_mount(mounts, add_cmd);

        assert_debug_snapshot!(mounts);

        let mv_cmd = MountCommand::MoveMount(
            MountPoint("/mnt/part3".into()),
            DevicePath("/dev/sde1".into()),
            FsType("ext4".to_string()),
            MountOpts("rw,relatime,data=ordered".to_string()),
            MountPoint("/mnt/part1".into()),
        );

        let mounts = update_mount(mounts, mv_cmd);

        assert_eq!(
            hashset!(Mount {
                target: MountPoint("/mnt/part3".into()),
                source: DevicePath("/dev/sde1".into()),
                fs_type: FsType("ext4".to_string()),
                opts: MountOpts("rw,relatime,data=ordered".to_string())
            }),
            mounts
        );

        let replace_cmd = MountCommand::ReplaceMount(
            MountPoint("/mnt/part3".into()),
            DevicePath("/dev/sde1".into()),
            FsType("ext4".to_string()),
            MountOpts("r,relatime,data=ordered".to_string()),
            MountOpts("rw,relatime,data=ordered".to_string()),
        );

        let mounts = update_mount(mounts, replace_cmd);

        assert_eq!(
            hashset!(Mount {
                target: MountPoint("/mnt/part3".into()),
                source: DevicePath("/dev/sde1".into()),
                fs_type: FsType("ext4".to_string()),
                opts: MountOpts("r,relatime,data=ordered".to_string())
            }),
            mounts
        );

        let rm_cmd = MountCommand::RemoveMount(
            MountPoint("/mnt/part3".into()),
            DevicePath("/dev/sde1".into()),
            FsType("ext4".to_string()),
            MountOpts("r,relatime,data=ordered".to_string()),
        );

        let mounts = update_mount(mounts, rm_cmd);
        assert_eq!(hashset!(), mounts);
    }
}
