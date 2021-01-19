// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::EmfAgentError, device_scanner_client, lustre::lctl};
use chrono::{DateTime, TimeZone, Utc};
use emf_wire_types::snapshot::{Create, Destroy, List, Mount, Snapshot, Unmount};
use futures::future::try_join_all;

type DeviceSnapshots = (String, DateTime<Utc>, DateTime<Utc>, Option<String>);

pub async fn list(l: List) -> Result<Vec<Snapshot>, EmfAgentError> {
    let mut args = vec!["--device", &l.target, "snapshot", "-l"];
    if let Some(name) = &l.name {
        args.push(name);
    }
    let stdout = lctl(args).await?;
    let stdout = stdout.trim();

    if stdout.is_empty() {
        return Ok(vec![]);
    }

    let mounts = device_scanner_client::get_snapshot_mounts().await?;

    let xs = parse_device_snapshots(stdout).into_iter().map(
        |(snapshot_name, create_time, modify_time, comment)| {
            build_snapshot(
                &l.target,
                snapshot_name,
                create_time,
                modify_time,
                comment,
                &mounts,
            )
        },
    );

    let snapshots = try_join_all(xs)
        .await?
        .into_iter()
        .filter_map(|x| x)
        .collect::<Vec<Snapshot>>();

    Ok(snapshots)
}

pub async fn create(c: Create) -> Result<(), EmfAgentError> {
    let use_barrier = match c.use_barrier {
        true => "on",
        false => "off",
    };

    let mut args = vec![
        "snapshot_create",
        "--fsname",
        &c.fsname,
        "--name",
        &c.name,
        "--barrier",
        use_barrier,
    ];

    if let Some(cmnt) = &c.comment {
        args.push("--comment");
        args.push(cmnt);
    }

    lctl(args).await.map(drop)
}

pub async fn destroy(d: Destroy) -> Result<(), EmfAgentError> {
    let mut args = vec!["snapshot_destroy", "--fsname", &d.fsname, "--name", &d.name];
    if d.force {
        args.push("--force");
    }
    lctl(args).await.map(drop)
}

pub async fn mount(m: Mount) -> Result<(), EmfAgentError> {
    let args = &["snapshot_mount", "--fsname", &m.fsname, "--name", &m.name];
    lctl(args).await.map(drop)
}

pub async fn unmount(u: Unmount) -> Result<(), EmfAgentError> {
    let args = &["snapshot_umount", "--fsname", &u.fsname, "--name", &u.name];
    lctl(args).await.map(drop)
}

async fn build_snapshot(
    target: &str,
    snapshot_name: String,
    create_time: DateTime<Utc>,
    modify_time: DateTime<Utc>,
    comment: Option<String>,
    mounts: &[device_types::mount::Mount],
) -> Result<Option<Snapshot>, EmfAgentError> {
    let mut fs_name = target.rsplitn(2, '-').nth(1).map(String::from);
    let filesystem_name = if let Some(name) = fs_name.take() {
        name
    } else {
        return Ok(None);
    };

    let snapshot_fsname = get_snapshot_label(&snapshot_name, &target).await?;
    let snapshot_fsname = if let Some(name) = snapshot_fsname {
        name
    } else {
        return Ok(None);
    };

    let mounted: bool = mounts
        .iter()
        .find_map(|x| {
            let s = x.opts.0.split(',').find(|x| x.starts_with("svname="))?;

            let s = s.split('=').nth(1)?.rsplitn(2, '-').nth(1)?;

            if s == snapshot_fsname {
                return Some(true);
            }

            None
        })
        .unwrap_or_default();

    Ok(Some(Snapshot {
        filesystem_name,
        snapshot_name,
        create_time,
        modify_time,
        comment,
        snapshot_fsname,
        mounted,
    }))
}

async fn get_snapshot_label(
    snapshot_name: &str,
    target: &str,
) -> Result<Option<String>, EmfAgentError> {
    let x = lctl(vec![
        "--device",
        target,
        "snapshot",
        "--get_label",
        snapshot_name,
    ])
    .await?;
    let x = x.trim().rsplitn(2, '-').nth(1).map(String::from);

    Ok(x)
}

fn parse_device_snapshots(x: &str) -> Vec<DeviceSnapshots> {
    x.trim()
        .lines()
        .map(|x| x.splitn(4, ' ').collect::<Vec<_>>())
        .filter_map(|xs| {
            let mut it = xs.into_iter();

            let name = it.next()?.to_string();
            let create = chrono::Utc.timestamp(it.next()?.parse().ok()?, 0);
            let update = chrono::Utc.timestamp(it.next()?.parse().ok()?, 0);
            let comment = it.next().map(String::from);

            Some((name, create, update, comment))
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_device_list() {
        let fixture = r#"
testsnapa 1604388443 1604388443
abcd 1604331109 1604331109
testabc 1604331284 1604331284
snaptwo 1604469817 1604469817
testabc4 1604332160 1604332160
1-es01a-2020-11-02T16:10:24Z 1604333425 1604333425 automatically created by EMF
1-es01a-2020-11-02T16:40:24Z 1604335225 1604335225 automatically created by EMF
snapone 1604469809 1604469809
testsnapz 1604468838 1604468838
1-es01a-2020-11-02T16:20:24Z 1604334025 1604334025 automatically created by EMF
1-es01a-2020-11-02T16:30:24Z 1604334625 1604334625 automatically created by EMF
1-es01a-2020-11-02T16:00:24Z 1604332825 1604332825 automatically created by EMF
snapthree 1604470070 1604470070
testsnapd 1604469760 1604469760
tstsnap 1604335880 1604335880
testsnapb 1604416099 1604416099
1-es01a-2020-11-02T15:50:24Z 1604332227 1604332227 automatically created by EMF
testabc3 1604331898 1604331898
mysnap 1604330923 1604330922 mynew snapshot
Test3 1604416497 1604416497
testsnap 1604330047 1604075186
        "#;
        let fixture = fixture;

        let xs = parse_device_snapshots(fixture);

        insta::assert_debug_snapshot!(xs);
    }
}
