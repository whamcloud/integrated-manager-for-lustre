// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::agent_error::ImlAgentError;
use futures::TryFutureExt;
use iml_cmd::{CheckedCommandExt, Command};
use iml_fs::read_file_to_end;
use iml_wire_types::client::{Mount, Unmount};
use std::io;
use tokio::{
    fs::{self, File},
    io::AsyncWriteExt,
};

static FSTAB_EDIT: &str = "/etc/fstab.iml.edit";
static FSTAB: &str = "/etc/fstab";

/// Given a mountpoint, this fn will check if it is mounted via `findmnt`.
/// It can optionally check `fstab` instead of the kernel.
async fn is_mounted(mountpoint: &str, check_fstab: bool) -> Result<bool, ImlAgentError> {
    let mut cmd = Command::new("/usr/bin/findmnt");

    if check_fstab {
        cmd.arg("--fstab");
    }

    let output = cmd
        .args(vec![
            "--target",
            &mountpoint,
            "--output",
            "TARGET",
            "--noheadings",
        ])
        .output()
        .await?;

    match output.status.code() {
        Some(0) => {
            let output = std::str::from_utf8(&output.stdout)?;

            Ok(output.lines().any(|x| x.trim() == mountpoint))
        }
        Some(1) => Ok(false),
        Some(code) => Err(ImlAgentError::Io(io::Error::new(
            io::ErrorKind::Other,
            format!("is_mounted: {} exited with code: {}", mountpoint, code),
        ))),
        None => Err(ImlAgentError::Io(io::Error::new(
            io::ErrorKind::Other,
            format!("is_mounted: {} was cancelled", mountpoint),
        ))),
    }
}

/// This action will attempt to:
/// - Create the specified `Mount.mountpoint` path
/// - Mount the client
/// - Add a systemd mount to `/etc/fstab`
/// - Optionally set systemd mount to start at boot iff `Mount.persist` is `true`.
///
/// Ref: http://wiki.lustre.org/Mounting_a_Lustre_File_System_on_Client_Nodes
pub async fn mount(mount: Mount) -> Result<(), ImlAgentError> {
    if is_mounted(&mount.mountpoint, false).await? {
        tracing::info!(
            "Mount command called for {}, but it was already mounted",
            mount.mountpoint
        );

        return Ok(());
    }

    // This should return Ok(()) if the dir already exists.
    fs::create_dir_all(&mount.mountpoint).await?;

    let args = vec!["-t", "lustre", &mount.mountspec, &mount.mountpoint];
    Command::new("/bin/mount")
        .args(args)
        .checked_output()
        .await?;

    update_fstab_entry(&mount.mountspec, &mount.mountpoint, mount.persist).await?;

    Ok(())
}

pub async fn mount_many(xs: Vec<Mount>) -> Result<(), ImlAgentError> {
    for x in xs {
        mount(x).await?;
    }

    Ok(())
}

pub async fn unmount(unmount: Unmount) -> Result<(), ImlAgentError> {
    delete_fstab_entry(&unmount.mountpoint).await?;

    Command::new("/bin/umount")
        .arg(unmount.mountpoint)
        .checked_output()
        .err_into()
        .await
        .map(drop)
}

/// This action will attempt to:
/// - Create the specified `Mount.mountpoint` path
/// - Add a systemd mount to `/etc/fstab`
/// - Optionally set systemd mount to start at boot iff `Mount.persist` is `true`.
pub async fn add_fstab_entry(mount: Mount) -> Result<(), ImlAgentError> {
    // This should return Ok(()) if the dir already exists.
    fs::create_dir_all(&mount.mountpoint).await?;

    update_fstab_entry(&mount.mountspec, &mount.mountpoint, mount.persist).await?;

    Ok(())
}

/// This action will attempt to:
/// - Remove a mountpoint from `/etc/fstab`
pub async fn remove_fstab_entry(mount: Mount) -> Result<(), ImlAgentError> {
    delete_fstab_entry(&mount.mountpoint).await?;

    Ok(())
}

pub async fn unmount_many(xs: Vec<Unmount>) -> Result<(), ImlAgentError> {
    for x in xs {
        unmount(x).await?;
    }

    Ok(())
}

async fn get_fstab() -> Result<String, ImlAgentError> {
    let contents = read_file_to_end(FSTAB).await?;
    let contents = String::from_utf8(contents)?;

    Ok(contents)
}

fn filter_mountpoint(mountpoint: &str, contents: &str) -> String {
    contents
        .split('\n')
        .filter(|x| match x.split_whitespace().nth(1) {
            Some(x) => x != mountpoint,
            None => true,
        })
        .collect::<Vec<_>>()
        .join("\n")
}

async fn write_fstab(contents: &str) -> Result<(), ImlAgentError> {
    let mut file = File::create(FSTAB_EDIT).await?;
    file.write_all(contents.as_bytes()).await?;

    fs::rename(FSTAB_EDIT, FSTAB).await?;

    Ok(())
}

async fn update_fstab_entry(
    mountspec: &str,
    mountpoint: &str,
    persist: bool,
) -> Result<(), ImlAgentError> {
    let persist = if persist { "" } else { "noauto," };

    delete_fstab_entry(mountpoint).await?;

    let contents = get_fstab()
        .await?
        .split('\n')
        .chain(std::iter::once(
            format!(
                "{}\t{}\tlustre\tx-systemd.mount-timeout=20m,{}_netdev",
                mountspec, mountpoint, persist,
            )
            .as_str(),
        ))
        .collect::<Vec<_>>()
        .join("\n");

    write_fstab(&contents).await?;

    Ok(())
}

async fn delete_fstab_entry(mountpoint: &str) -> Result<(), ImlAgentError> {
    let contents = get_fstab().await?;
    let new_contents = filter_mountpoint(mountpoint, &contents);

    if contents != new_contents {
        write_fstab(&new_contents).await?;
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_filter() {
        let fstab = r#"# /etc/fstab
# blah

/dev/foo        /bar        something   defaults    1 1
1.2.3.4@tcp:/foobar              /mnt/lustre_clients/foobar          lustre      x-systemd.mount-timeout=20m,noauto,_netdev
1.2.3.4@tcp:/foobar1             /mnt/lustre_clients/foobar1         lustre      x-systemd.mount-timeout=20m,_netdev

1.2.3.4:/baz    /qux        nfs         defaults    0 0

"#;

        insta::assert_display_snapshot!(filter_mountpoint("/mnt/lustre_clients/foobar", fstab));
        insta::assert_display_snapshot!(filter_mountpoint("/mnt/lustre_clients/foobar1", fstab));

        let no_match = filter_mountpoint("qux", fstab);
        insta::assert_display_snapshot!(no_match);

        assert_eq!(fstab, no_match);
    }
}
