// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

//! Handles Updates of state
//!
//! `device-scanner` uses a persistent streaming strategy
//! where Unix domain sockets can connect and be fed device-graph changes as they occur.

use crate::error::{self, Result};
use device_types::{
    devices::{Device, LogicalVolume, MdRaid, Mpath, Partition, Root, ScsiDevice, VolumeGroup},
    mount::Mount,
    state,
    uevent::UEvent,
    DevicePath,
};
use im::{ordset, vector, HashSet, OrdSet, Vector};

/// Filter out any devices that are not suitable for mounting a filesystem.
fn keep_usable(x: &UEvent) -> bool {
    x.size != Some(0) && x.size.is_some() && x.read_only != Some(true) && x.bios_boot != Some(true)
}

fn is_mpath(x: &UEvent) -> bool {
    x.is_mpath == Some(true)
}

fn is_dm(x: &UEvent) -> bool {
    [&x.lv_uuid, &x.vg_uuid, &x.dm_lv_name]
        .iter()
        .all(|x| x.is_some())
}

fn is_partition(x: &UEvent) -> bool {
    x.part_entry_mm.is_some()
}

fn is_mdraid(x: &UEvent) -> bool {
    x.md_uuid.is_some()
}

fn format_major_minor(major: &str, minor: &str) -> String {
    format!("{}:{}", major, minor)
}

fn find_by_major_minor(xs: &Vector<String>, major: &str, minor: &str) -> bool {
    xs.contains(&format_major_minor(major, minor))
}

fn find_mount<'a>(xs: &OrdSet<DevicePath>, ys: &'a HashSet<Mount>) -> Option<&'a Mount> {
    ys.iter()
        .find(|Mount { source, .. }| xs.iter().any(|x| x == source))
}

fn get_vgs(b: &Buckets, major: &str, minor: &str) -> Result<HashSet<Device>> {
    b.dms
        .iter()
        .filter(|&x| find_by_major_minor(&x.dm_slave_mms, major, minor))
        .map(|x| {
            Ok(Device::VolumeGroup(VolumeGroup {
                name: x
                    .dm_vg_name
                    .clone()
                    .ok_or_else(|| error::none_error("Expected dm_vg_name"))?,
                children: ordset![],
                size: x
                    .dm_vg_size
                    .ok_or_else(|| error::none_error("Expected Size"))?,
                uuid: x
                    .vg_uuid
                    .clone()
                    .ok_or_else(|| error::none_error("Expected vg_uuid"))?,
            }))
        })
        .collect()
}

fn get_partitions(
    b: &Buckets,
    ys: &HashSet<Mount>,
    major: &str,
    minor: &str,
) -> Result<HashSet<Device>> {
    b.partitions
        .iter()
        .filter(|&x| match x.part_entry_mm {
            Some(ref p) => p == &format_major_minor(major, minor),
            None => false,
        })
        .map(|x| {
            let mount = find_mount(&x.paths, ys);

            Ok(Device::Partition(Partition {
                serial: x.scsi83.clone(),
                scsi80: x.scsi80.clone(),
                partition_number: x
                    .part_entry_number
                    .ok_or_else(|| error::none_error("Expected part_entry_number"))?,
                devpath: x.devpath.clone(),
                major: x.major.clone(),
                minor: x.minor.clone(),
                size: x.size.ok_or_else(|| error::none_error("Expected size"))?,
                paths: x.paths.clone(),
                filesystem_type: x.fs_type.clone(),
                fs_uuid: x.fs_uuid.clone(),
                fs_label: x.fs_label.clone(),
                children: ordset![],
                mount: mount.map(ToOwned::to_owned),
            }))
        })
        .collect()
}

fn get_lvs(b: &Buckets, ys: &HashSet<Mount>, uuid: &str) -> Result<HashSet<Device>> {
    b.dms
        .iter()
        .filter(|&x| match x.vg_uuid {
            Some(ref p) => p == uuid,
            None => false,
        })
        .map(|x| {
            let mount = find_mount(&x.paths, ys);

            Ok(Device::LogicalVolume(LogicalVolume {
                name: x
                    .dm_lv_name
                    .clone()
                    .ok_or_else(|| error::none_error("Expected dm_lv_name"))?,
                devpath: x.devpath.clone(),
                uuid: x
                    .lv_uuid
                    .clone()
                    .ok_or_else(|| error::none_error("Expected lv_uuid"))?,
                size: x.size.ok_or_else(|| error::none_error("Expected size"))?,
                major: x.major.clone(),
                minor: x.minor.clone(),
                paths: x.paths.clone(),
                mount: mount.map(ToOwned::to_owned),
                filesystem_type: x.fs_type.clone(),
                fs_uuid: x.fs_uuid.clone(),
                fs_label: x.fs_label.clone(),
                children: ordset![],
            }))
        })
        .collect()
}

fn get_scsis(b: &Buckets, ys: &HashSet<Mount>) -> Result<HashSet<Device>> {
    b.rest
        .iter()
        .map(|x| {
            let mount = find_mount(&x.paths, ys);

            Ok(Device::ScsiDevice(ScsiDevice {
                serial: x.scsi83.clone(),
                scsi80: x.scsi80.clone(),
                devpath: x.devpath.clone(),
                major: x.major.clone(),
                minor: x.minor.clone(),
                size: x.size.ok_or_else(|| error::none_error("Expected size"))?,
                filesystem_type: x.fs_type.clone(),
                fs_uuid: x.fs_uuid.clone(),
                fs_label: x.fs_label.clone(),
                paths: x.paths.clone(),
                children: ordset![],
                mount: mount.map(ToOwned::to_owned),
            }))
        })
        .collect()
}

fn get_mpaths(
    b: &Buckets,
    ys: &HashSet<Mount>,
    major: &str,
    minor: &str,
) -> Result<HashSet<Device>> {
    b.mpaths
        .iter()
        .filter(|&x| find_by_major_minor(&x.dm_slave_mms, major, minor))
        .map(|x| {
            let mount = find_mount(&x.paths, ys);

            Ok(Device::Mpath(Mpath {
                serial: x.scsi83.clone(),
                scsi80: x.scsi80.clone(),
                dm_name: x
                    .dm_name
                    .clone()
                    .ok_or_else(|| error::none_error("Mpath device did not have a name"))?,
                size: x.size.ok_or_else(|| error::none_error("Expected size"))?,
                major: x.major.clone(),
                minor: x.minor.clone(),
                paths: x.paths.clone(),
                filesystem_type: x.fs_type.clone(),
                fs_uuid: x.fs_uuid.clone(),
                fs_label: x.fs_label.clone(),
                children: ordset![],
                devpath: x.devpath.clone(),
                mount: mount.map(ToOwned::to_owned),
            }))
        })
        .collect()
}

fn get_mds(
    b: &Buckets,
    ys: &HashSet<Mount>,
    paths: &OrdSet<DevicePath>,
) -> Result<HashSet<Device>> {
    b.mds
        .iter()
        .filter(|&x| paths.clone().intersection(x.md_devs.clone()).is_empty())
        .map(|x| {
            let mount = find_mount(&x.paths, ys);

            Ok(Device::MdRaid(MdRaid {
                paths: x.paths.clone(),
                filesystem_type: x.fs_type.clone(),
                fs_uuid: x.fs_uuid.clone(),
                fs_label: x.fs_label.clone(),
                mount: mount.map(ToOwned::to_owned),
                major: x.major.clone(),
                minor: x.minor.clone(),
                size: x.size.ok_or_else(|| error::none_error("Expected size"))?,
                children: ordset![],
                uuid: x
                    .md_uuid
                    .clone()
                    .ok_or_else(|| error::none_error("Expected md_uuid"))?,
            }))
        })
        .collect()
}

fn build_device_graph<'a>(ptr: &mut Device, b: &Buckets<'a>, ys: &HashSet<Mount>) -> Result<()> {
    match ptr {
        Device::Root(r) => {
            let ss = get_scsis(&b, &ys)?;

            for mut x in ss {
                build_device_graph(&mut x, b, ys)?;

                r.children.insert(x);
            }

            Ok(())
        }
        Device::Mpath(Mpath {
            children,
            major,
            minor,
            paths,
            ..
        }) => {
            let vs = get_vgs(&b, major, minor)?;

            let ps = get_partitions(&b, &ys, major, minor)?;

            let mds = get_mds(&b, &ys, &paths)?;

            for mut x in HashSet::unions(vec![vs, ps, mds]) {
                build_device_graph(&mut x, b, ys)?;

                children.insert(x);
            }

            Ok(())
        }
        Device::ScsiDevice(ScsiDevice {
            children,
            paths,
            major,
            minor,
            ..
        })
        | Device::Partition(Partition {
            children,
            paths,
            major,
            minor,
            ..
        }) => {
            let xs = get_partitions(&b, &ys, &major, &minor)?;

            // This should only be present for scsi devs
            let ms = get_mpaths(&b, &ys, major, minor)?;

            let vs = get_vgs(b, major, minor)?;

            let mds = get_mds(&b, &ys, &paths)?;

            for mut x in HashSet::unions(vec![xs, ms, vs, mds]) {
                build_device_graph(&mut x, b, ys)?;

                children.insert(x);
            }

            Ok(())
        }
        Device::VolumeGroup(VolumeGroup { children, uuid, .. }) => {
            let lvs = get_lvs(&b, &ys, &uuid)?;

            for mut x in lvs {
                build_device_graph(&mut x, b, ys)?;

                children.insert(x);
            }

            Ok(())
        }
        Device::LogicalVolume(LogicalVolume {
            major,
            minor,
            children,
            ..
        }) => {
            let ps = get_partitions(&b, &ys, &major, &minor)?;

            for mut x in ps {
                build_device_graph(&mut x, b, ys)?;

                children.insert(x);
            }

            Ok(())
        }
        Device::MdRaid(MdRaid {
            major,
            minor,
            children,
            paths,
            ..
        }) => {
            let vs = get_vgs(&b, &major, &minor)?;

            let ps = get_partitions(&b, &ys, major, minor)?;

            let mds = get_mds(&b, &ys, &paths)?;

            for mut x in HashSet::unions(vec![vs, ps, mds]) {
                build_device_graph(&mut x, b, ys)?;

                children.insert(x);
            }

            Ok(())
        }
    }
}

#[derive(Debug)]
struct Buckets<'a> {
    dms: Vector<&'a UEvent>,
    mds: Vector<&'a UEvent>,
    mpaths: Vector<&'a UEvent>,
    partitions: Vector<&'a UEvent>,
    rest: Vector<&'a UEvent>,
}

fn bucket_devices<'a>(xs: &Vector<&'a UEvent>) -> Buckets<'a> {
    let buckets = Buckets {
        dms: vector![],
        mds: vector![],
        mpaths: vector![],
        partitions: vector![],
        rest: vector![],
    };

    let buckets = xs.iter().fold(buckets, |mut acc, x| {
        if is_dm(&x) {
            acc.dms.push_back(x)
        } else if is_mdraid(&x) {
            acc.mds.push_back(x)
        } else if is_mpath(&x) {
            acc.mpaths.push_back(x)
        } else if is_partition(&x) {
            acc.partitions.push_back(x)
        } else {
            acc.rest.push_back(x)
        }

        acc
    });

    buckets
}

fn build_device_list(xs: &state::UEvents) -> Vector<&UEvent> {
    xs.values().filter(|y| keep_usable(y)).collect()
}

pub fn produce_device_graph(state: &state::State) -> Result<bytes::Bytes> {
    let dev_list = build_device_list(&state.uevents);
    let dev_list = bucket_devices(&dev_list);

    let mut root = Device::Root(Root::default());

    build_device_graph(&mut root, &dev_list, &state.local_mounts)?;

    let v = serde_json::to_string(&(&root, &state.local_mounts))?;
    let b = bytes::BytesMut::from((v + "\n").as_str());
    Ok(b.freeze())
}
