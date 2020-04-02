// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use device_types::{
    devices::{
        Dataset, Device, LogicalVolume, MdRaid, Mpath, Partition, Root, ScsiDevice, VolumeGroup,
        Zpool,
    },
    get_vdev_paths,
    mount::{FsType, Mount, MountPoint},
    DevicePath,
};
use iml_wire_types::Fqdn;
use std::{
    cmp::Ordering,
    collections::{BTreeMap, BTreeSet, HashMap},
    fmt::Display,
    hash::{Hash, Hasher},
};

#[derive(Debug, Clone, Eq, serde::Serialize)]
pub struct MajorMinor(pub String);

impl Ord for MajorMinor {
    fn cmp(&self, other: &MajorMinor) -> Ordering {
        self.0.partial_cmp(&other.0).unwrap()
    }
}

impl PartialOrd for MajorMinor {
    fn partial_cmp(&self, other: &MajorMinor) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl PartialEq for MajorMinor {
    fn eq(&self, other: &MajorMinor) -> bool {
        self.0 == other.0
    }
}

impl Hash for MajorMinor {
    fn hash<H: Hasher>(&self, h: &mut H) {
        self.0.hash(h)
    }
}

impl<D1: Display, D2: Display> From<(D1, D2)> for MajorMinor {
    fn from((major, minor): (D1, D2)) -> MajorMinor {
        MajorMinor(format!("{}:{}", major, minor))
    }
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct LinuxPluginMpathDevice<'a> {
    name: &'a str,
    block_device: MajorMinor,
    nodes: BTreeSet<LinuxPluginDevice<'a>>,
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct LinuxPluginVgDevice<'a> {
    name: &'a str,
    uuid: &'a str,
    size: u64,
    pvs_major_minor: BTreeSet<MajorMinor>,
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct LinuxPluginLvDevice<'a> {
    block_device: MajorMinor,
    size: u64,
    uuid: &'a str,
    name: &'a str,
}

#[derive(Debug, Eq, PartialEq, Clone, serde::Serialize)]
pub struct LinuxPluginDevice<'a> {
    major_minor: MajorMinor,
    parent: Option<MajorMinor>,
    partition_number: Option<u64>,
    path: &'a DevicePath,
    paths: BTreeSet<&'a DevicePath>,
    serial_83: &'a Option<String>,
    serial_80: &'a Option<String>,
    size: Option<u64>,
    filesystem_type: &'a Option<String>,
}

#[derive(Debug, Eq, PartialEq, Clone, serde::Serialize)]
pub struct LinuxPluginZpool<'a> {
    block_device: MajorMinor,
    drives: BTreeSet<MajorMinor>,
    name: &'a str,
    path: &'a str,
    size: u64,
    uuid: u64,
}

#[derive(Debug, Clone, serde::Serialize)]
#[serde(untagged)]
pub enum LinuxPluginItem<'a> {
    LinuxPluginDevice(LinuxPluginDevice<'a>),
    LinuxPluginZpool(LinuxPluginZpool<'a>),
}

impl<'a> Ord for LinuxPluginDevice<'a> {
    fn cmp(&self, other: &LinuxPluginDevice) -> Ordering {
        self.major_minor.partial_cmp(&other.major_minor).unwrap()
    }
}

impl<'a> PartialOrd for LinuxPluginDevice<'a> {
    fn partial_cmp(&self, other: &LinuxPluginDevice) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct LinuxPluginData<'a> {
    pub devs: BTreeMap<MajorMinor, LinuxPluginItem<'a>>,
    pub local_fs: BTreeMap<MajorMinor, (&'a MountPoint, &'a FsType)>,
    pub mpath: BTreeMap<&'a str, LinuxPluginMpathDevice<'a>>,
    pub vgs: BTreeMap<&'a str, LinuxPluginVgDevice<'a>>,
    pub lvs: BTreeMap<&'a str, BTreeMap<&'a str, LinuxPluginLvDevice<'a>>>,
    pub zfspools: BTreeMap<u64, LinuxPluginZpool<'a>>,
    pub zfsdatasets: BTreeMap<u64, LinuxPluginZpool<'a>>,
}

impl<'a> Default for LinuxPluginData<'a> {
    fn default() -> LinuxPluginData<'a> {
        LinuxPluginData {
            devs: BTreeMap::new(),
            local_fs: BTreeMap::new(),
            mpath: BTreeMap::new(),
            vgs: BTreeMap::new(),
            lvs: BTreeMap::new(),
            zfspools: BTreeMap::new(),
            zfsdatasets: BTreeMap::new(),
        }
    }
}

impl<'a> From<&'a ScsiDevice> for LinuxPluginDevice<'a> {
    fn from(s: &ScsiDevice) -> LinuxPluginDevice {
        LinuxPluginDevice {
            major_minor: (&s.major, &s.minor).into(),
            parent: None,
            path: s.paths.get_min().unwrap(),
            paths: s.paths.iter().collect(),
            partition_number: None,
            serial_83: &s.serial,
            serial_80: &s.scsi80,
            size: Some(s.size),
            filesystem_type: &s.filesystem_type,
        }
    }
}

impl<'a> From<(&'a Partition, Option<&LinuxPluginDevice<'a>>)> for LinuxPluginDevice<'a> {
    fn from((x, p): (&'a Partition, Option<&LinuxPluginDevice>)) -> LinuxPluginDevice<'a> {
        LinuxPluginDevice {
            major_minor: (&x.major, &x.minor).into(),
            parent: p.map(|y| y.major_minor.clone()),
            path: x.paths.get_min().unwrap(),
            paths: x.paths.iter().collect(),
            partition_number: Some(x.partition_number),
            serial_83: &None,
            serial_80: &None,
            size: Some(x.size),
            filesystem_type: &x.filesystem_type,
        }
    }
}

impl<'a> From<(&'a Mpath, Option<&LinuxPluginDevice<'a>>)> for LinuxPluginDevice<'a> {
    fn from((x, _p): (&'a Mpath, Option<&LinuxPluginDevice>)) -> LinuxPluginDevice<'a> {
        LinuxPluginDevice {
            major_minor: (&x.major, &x.minor).into(),
            // @FIXME
            // linux.py erroneously declares that
            // only partitions should have a parent.
            // To make interop work with this assumption
            // we set the parent to `None`.
            // https://github.com/whamcloud/integrated-manager-for-lustre/blob/841567bb99edde5b635fb1573a6485f6eb75428a/chroma_core/plugins/linux.py#L439
            parent: None,
            path: x.paths.get_min().unwrap(),
            paths: x.paths.iter().collect(),
            partition_number: None,
            serial_83: &x.serial,
            serial_80: &x.scsi80,
            size: Some(x.size),
            filesystem_type: &x.filesystem_type,
        }
    }
}

impl<'a> From<(&'a LogicalVolume, Option<&LinuxPluginDevice<'a>>)> for LinuxPluginDevice<'a> {
    fn from((x, _p): (&'a LogicalVolume, Option<&LinuxPluginDevice>)) -> LinuxPluginDevice<'a> {
        LinuxPluginDevice {
            major_minor: ("lv", &x.uuid).into(),
            // @FIXME
            // linux.py erroneously declares that
            // only partitions should have a parent.
            // To make interop work with this assumption
            // we set the parent to `None`.
            // https://github.com/whamcloud/integrated-manager-for-lustre/blob/841567bb99edde5b635fb1573a6485f6eb75428a/chroma_core/plugins/linux.py#L439
            parent: None,
            path: x.paths.get_min().unwrap(),
            paths: x.paths.iter().collect(),
            partition_number: None,
            serial_83: &None,
            serial_80: &None,
            size: Some(x.size),
            filesystem_type: &x.filesystem_type,
        }
    }
}

impl<'a> From<&'a Zpool> for LinuxPluginZpool<'a> {
    fn from(x: &'a Zpool) -> LinuxPluginZpool<'a> {
        LinuxPluginZpool {
            name: &x.name,
            path: &x.name,
            block_device: ("zfspool", &x.guid).into(),
            size: x.size,
            uuid: x.guid,
            drives: BTreeSet::new(),
        }
    }
}

impl<'a> From<(&'a Dataset, u64)> for LinuxPluginZpool<'a> {
    fn from((x, size): (&'a Dataset, u64)) -> LinuxPluginZpool<'a> {
        LinuxPluginZpool {
            name: &x.name,
            path: &x.name,
            block_device: ("zfsset", &x.guid).into(),
            size,
            uuid: x.guid,
            drives: BTreeSet::new(),
        }
    }
}

fn add_mount<'a>(
    mount: &'a Mount,
    d: &LinuxPluginDevice<'a>,
    linux_plugin_data: &mut LinuxPluginData<'a>,
) {
    // This check is working around one cause of https://github.com/whamcloud/integrated-manager-for-lustre/issues/895
    // Once we persist device-scanner input directly in the IML database, we won't need this fn anymore,
    // as device-scanner correctly reports that the mount is transient.
    if mount.target.0.as_os_str().len() == 14
        && mount.target.0.to_string_lossy().starts_with("/tmp/mnt")
    {
        return;
    }

    linux_plugin_data
        .local_fs
        .insert(d.major_minor.clone(), (&mount.target, &mount.fs_type));
}

pub fn populate_zpool<'a>(
    x: &'a Zpool,
    mm: MajorMinor,
    linux_plugin_data: &mut LinuxPluginData<'a>,
) {
    if x.children.is_empty() {
        let pool = linux_plugin_data
            .devs
            .entry(("zfspool", x.guid).into())
            .or_insert_with(|| LinuxPluginItem::LinuxPluginZpool(x.into()));

        if let LinuxPluginItem::LinuxPluginZpool(p) = pool {
            p.drives.insert(mm.clone());

            let p2 = linux_plugin_data
                .zfspools
                .entry(p.uuid)
                .or_insert_with(|| p.clone());

            p2.drives.insert(mm);
        };
    } else {
        for dev in &x.children {
            if let Device::Dataset(d) = dev {
                let dataset = linux_plugin_data
                    .devs
                    .entry(("zfsset", d.guid).into())
                    .or_insert_with(|| LinuxPluginItem::LinuxPluginZpool((d, x.size).into()));

                if let LinuxPluginItem::LinuxPluginZpool(d) = dataset {
                    d.drives.insert(mm.clone());

                    let d2 = linux_plugin_data
                        .zfsdatasets
                        .entry(d.uuid)
                        .or_insert_with(|| d.clone());

                    d2.drives.insert(mm.clone());
                };
            }
        }
    }
}

pub fn devtree2linuxoutput<'a>(
    device: &'a Device,
    parent: Option<&LinuxPluginDevice<'a>>,
    mut linux_plugin_data: &mut LinuxPluginData<'a>,
) {
    match device {
        Device::Root(x) => {
            for c in &x.children {
                devtree2linuxoutput(c, None, &mut linux_plugin_data);
            }
        }
        Device::ScsiDevice(x) => {
            let d: LinuxPluginDevice = x.into();

            if let Some(mount) = &x.mount {
                add_mount(mount, &d, linux_plugin_data);
            }

            for c in &x.children {
                devtree2linuxoutput(&c, Some(&d), &mut linux_plugin_data);
            }

            linux_plugin_data
                .devs
                .insert(d.major_minor.clone(), LinuxPluginItem::LinuxPluginDevice(d));
        }
        Device::Partition(x) => {
            let d: LinuxPluginDevice = (x, parent).into();

            if let Some(mount) = &x.mount {
                add_mount(mount, &d, linux_plugin_data);
            }

            for c in &x.children {
                devtree2linuxoutput(c, Some(&d), &mut linux_plugin_data);
            }

            linux_plugin_data
                .devs
                .insert(d.major_minor.clone(), LinuxPluginItem::LinuxPluginDevice(d));
        }
        Device::Mpath(x) => {
            let d: LinuxPluginDevice<'a> = (x, parent).into();

            if let Some(mount) = &x.mount {
                add_mount(mount, &d, linux_plugin_data);
            }

            for c in &x.children {
                devtree2linuxoutput(c, Some(&d), &mut linux_plugin_data);
            }

            let block_device = d.major_minor.clone();

            linux_plugin_data
                .devs
                .insert(d.major_minor.clone(), LinuxPluginItem::LinuxPluginDevice(d));

            let mpath_device =
                linux_plugin_data
                    .mpath
                    .entry(&x.dm_name)
                    .or_insert(LinuxPluginMpathDevice {
                        block_device,
                        name: &x.dm_name,
                        nodes: BTreeSet::new(),
                    });

            if let Some(parent) = parent {
                mpath_device.nodes.insert(parent.clone());
            }
        }
        Device::VolumeGroup(x) => {
            let vg_device = linux_plugin_data
                .vgs
                .entry(&x.name)
                .or_insert(LinuxPluginVgDevice {
                    name: &x.name,
                    size: x.size,
                    uuid: &x.uuid,
                    pvs_major_minor: BTreeSet::new(),
                });

            if let Some(parent) = parent {
                vg_device.pvs_major_minor.insert(parent.major_minor.clone());
            }

            x.children
                .iter()
                .filter_map(|d| match d {
                    Device::LogicalVolume(lv) => Some(lv),
                    _ => None,
                })
                .for_each(|lv| {
                    let d: LinuxPluginDevice = (lv, parent).into();

                    if let Some(mount) = &lv.mount {
                        add_mount(mount, &d, linux_plugin_data);
                    }

                    for c in &lv.children {
                        devtree2linuxoutput(c, Some(&d), &mut linux_plugin_data);
                    }

                    let block_device = d.major_minor.clone();

                    linux_plugin_data
                        .devs
                        .insert(d.major_minor.clone(), LinuxPluginItem::LinuxPluginDevice(d));

                    linux_plugin_data
                        .lvs
                        .entry(&x.name)
                        .or_insert_with(BTreeMap::new)
                        .entry(&lv.name)
                        .or_insert(LinuxPluginLvDevice {
                            name: &lv.name,
                            size: lv.size,
                            uuid: &lv.uuid,
                            block_device,
                        });
                });
        }
        Device::Zpool(x) => {
            populate_zpool(x, parent.unwrap().major_minor.clone(), linux_plugin_data);
        }
        _ => {}
    };
}

type PoolMap<'a> = BTreeMap<u64, (&'a Zpool, BTreeSet<DevicePath>)>;

pub fn build_device_lookup<'a>(
    dev_tree: &'a Device,
    path_map: &mut BTreeMap<&'a DevicePath, MajorMinor>,
    pool_map: &mut PoolMap<'a>,
) {
    match dev_tree {
        Device::Root(Root { children }) | Device::VolumeGroup(VolumeGroup { children, .. }) => {
            for c in children {
                build_device_lookup(c, path_map, pool_map);
            }
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
        })
        | Device::MdRaid(MdRaid {
            children,
            paths,
            major,
            minor,
            ..
        })
        | Device::Mpath(Mpath {
            children,
            paths,
            major,
            minor,
            ..
        }) => {
            for p in paths {
                path_map.insert(p, (major, minor).into());
            }

            for c in children {
                build_device_lookup(c, path_map, pool_map);
            }
        }
        Device::LogicalVolume(LogicalVolume {
            children,
            paths,
            uuid,
            ..
        }) => {
            for p in paths {
                path_map.insert(p, ("lv", uuid).into());
            }

            for c in children {
                build_device_lookup(c, path_map, pool_map);
            }
        }
        Device::Zpool(x) => {
            let paths = get_vdev_paths(&x.vdev);

            pool_map.entry(x.guid).or_insert_with(|| (x, paths));
        }
        Device::Dataset(_) => {}
    }
}

/// In order for a pool to exist on > 1 node, *all* of it's backing
/// storage must exist on > 1 host.
///
/// This fn figures out if all of a pools VDEVs exist on
/// multiple hosts and if so, returns
/// where they need to be inserted.
pub fn get_shared_pools<'a, S: ::std::hash::BuildHasher>(
    host: &Fqdn,
    path_map: &'a BTreeMap<&'a DevicePath, MajorMinor>,
    cluster_pools: &'a HashMap<&'a Fqdn, PoolMap<'a>, S>,
) -> Vec<(&'a Zpool, MajorMinor)> {
    let mut shared_pools: Vec<_> = vec![];

    let paths: BTreeSet<&DevicePath> = path_map.keys().copied().collect();

    for (&h, ps) in cluster_pools.iter() {
        if host == h {
            continue;
        }

        for v in ps.values() {
            let ds = v.1.iter().collect();

            if !paths.is_superset(&ds) {
                continue;
            };

            tracing::debug!("pool is shared between {} and {}", h, host);

            for d in ds {
                let parent = path_map[&d].clone();

                shared_pools.push((v.0, parent));
            }
        }
    }

    shared_pools
}

/// Given a slice of major minors,
/// figures out all cooresponding the device paths and returns them.
fn major_minors_to_dev_paths<'a>(
    xs: &BTreeSet<MajorMinor>,
    path_map: &BTreeMap<&'a DevicePath, MajorMinor>,
) -> BTreeSet<&'a DevicePath> {
    xs.iter().fold(BTreeSet::new(), |acc, mm| {
        let paths = path_map
            .iter()
            .filter(|(_, pmm)| &mm == pmm)
            .map(|(p, _)| *p)
            .collect();

        acc.union(&paths).copied().collect()
    })
}

/// Given some aggregated data
/// Figure out what VGs can be shared between hosts and add them to the other hosts.
pub fn update_vgs<'a>(
    mut xs: BTreeMap<&'a Fqdn, LinuxPluginData<'a>>,
    path_map: &HashMap<&'a Fqdn, BTreeMap<&'a DevicePath, MajorMinor>>,
) -> BTreeMap<&'a Fqdn, LinuxPluginData<'a>> {
    let shared_vgs = xs.iter().fold(vec![], |mut acc, (from_host, x)| {
        let from_paths = &path_map[from_host];

        let mut others: Vec<_> = xs
            .iter()
            .filter(|(k, _)| k != &from_host)
            .filter_map(|(to_host, _)| {
                let to_paths: BTreeSet<&DevicePath> =
                    (&path_map[to_host]).keys().copied().collect();

                let shared_vgs: Vec<_> = x
                    .vgs
                    .iter()
                    .filter(|(_, vg)| {
                        let p = major_minors_to_dev_paths(&vg.pvs_major_minor, &from_paths);

                        to_paths.is_superset(&p)
                    })
                    .map(|(vg_name, _)| (Fqdn::clone(from_host), Fqdn::clone(to_host), *vg_name))
                    .collect();

                if shared_vgs.is_empty() {
                    None
                } else {
                    Some(shared_vgs)
                }
            })
            .flatten()
            .collect();

        acc.append(&mut others);

        acc
    });

    for (from_host, to_host, vg_name) in shared_vgs {
        let from = xs.get(&from_host).unwrap();

        let vg = from.vgs.get(&vg_name).cloned().unwrap();

        let lvs = from.lvs.get(&vg_name).cloned();

        let lv_devs: Option<Vec<_>> = lvs.as_ref().map(|lvs| {
            lvs.iter()
                .map(|(_, lv)| {
                    (
                        lv.block_device.clone(),
                        from.devs.get(&lv.block_device).cloned().unwrap_or_else(|| {
                            panic!("Did not find lv block device {:?}", lv.block_device)
                        }),
                    )
                })
                .collect()
        });

        let to = xs.get_mut(&to_host).unwrap();

        to.vgs.insert(vg_name, vg);

        if let Some(lvs) = lvs {
            to.lvs.insert(vg_name, lvs);
        }

        if let Some(lv_devs) = lv_devs {
            for (mm, lv_dev) in lv_devs {
                to.devs.insert(mm, lv_dev);
            }
        }
    }

    xs
}

#[cfg(test)]
mod tests {
    use super::{devtree2linuxoutput, LinuxPluginData};
    use device_types::devices::Device;
    use insta::assert_json_snapshot;

    #[test]
    fn test_devtree2linuxoutput() {
        let device:Device = serde_json::from_str(r#"
{
  "Root": {
    "children": [
      {
        "ScsiDevice": {
          "serial": "36001405aa1a4a2010734758a9e57c178",
          "scsi80": "SLIO-ORG ost5            aa1a4a20-1073-4758-a9e5-7c178c6ed8ef",
          "major": "8",
          "minor": "160",
          "devpath": "/devices/platform/host5/session4/target5:0:0/5:0:0:4/block/sdk",
          "size": 5368709120,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-36001405aa1a4a2010734758a9e57c178",
            "/dev/disk/by-id/wwn-0x6001405aa1a4a2010734758a9e57c178",
            "/dev/disk/by-path/ip-10.73.50.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:oss-lun-4",
            "/dev/sdk"
          ],
          "mount": null,
          "children": [
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-14",
                "serial": "36001405aa1a4a2010734758a9e57c178",
                "scsi80": "SLIO-ORG ost5            aa1a4a20-1073-4758-a9e5-7c178c6ed8ef",
                "dm_name": "mpatho",
                "size": 5368709120,
                "major": "253",
                "minor": "14",
                "filesystem_type": null,
                "paths": [
                  "/dev/mapper/mpatho",
                  "/dev/disk/by-id/dm-name-mpatho",
                  "/dev/disk/by-id/dm-uuid-mpath-36001405aa1a4a2010734758a9e57c178",
                  "/dev/dm-14"
                ],
                "children": [],
                "mount": null
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "3600140598252aa12555428f94b6ea915",
          "scsi80": "SLIO-ORG ost16           98252aa1-2555-428f-94b6-ea915aadcd5a",
          "major": "66",
          "minor": "0",
          "devpath": "/devices/platform/host5/session4/target5:0:0/5:0:0:15/block/sdag",
          "size": 5368709120,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-3600140598252aa12555428f94b6ea915",
            "/dev/disk/by-id/wwn-0x600140598252aa12555428f94b6ea915",
            "/dev/disk/by-path/ip-10.73.50.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:oss-lun-15",
            "/dev/sdag"
          ],
          "mount": null,
          "children": [
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-7",
                "serial": "3600140598252aa12555428f94b6ea915",
                "scsi80": "SLIO-ORG ost16           98252aa1-2555-428f-94b6-ea915aadcd5a",
                "dm_name": "mpathh",
                "size": 5368709120,
                "major": "253",
                "minor": "7",
                "filesystem_type": "LVM2_member",
                "paths": [
                  "/dev/mapper/mpathh",
                  "/dev/disk/by-id/dm-name-mpathh",
                  "/dev/disk/by-id/dm-uuid-mpath-3600140598252aa12555428f94b6ea915",
                  "/dev/disk/by-id/lvm-pv-uuid-sSb1jT-hBLl-am3F-mc9T-2cMR-oGbb-xG0FZw",
                  "/dev/dm-7"
                ],
                "children": [],
                "mount": {
                  "source": "/dev/dm-7",
                  "target": "/tmp/mnt9aU7P6",
                  "fs_type": "xfs",
                  "opts": "rw,relatime,seclabel,attr2,inode64,noquota"
                }
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "360014054e9b5031f3434c56a0746de1f",
          "scsi80": "SLIO-ORG ost7            4e9b5031-f343-4c56-a074-6de1feb8f72c",
          "major": "8",
          "minor": "224",
          "devpath": "/devices/platform/host5/session4/target5:0:0/5:0:0:6/block/sdo",
          "size": 5368709120,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-360014054e9b5031f3434c56a0746de1f",
            "/dev/disk/by-id/wwn-0x60014054e9b5031f3434c56a0746de1f",
            "/dev/disk/by-path/ip-10.73.50.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:oss-lun-6",
            "/dev/sdo"
          ],
          "mount": null,
          "children": [
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-16",
                "serial": "360014054e9b5031f3434c56a0746de1f",
                "scsi80": "SLIO-ORG ost7            4e9b5031-f343-4c56-a074-6de1feb8f72c",
                "dm_name": "mpathq",
                "size": 5368709120,
                "major": "253",
                "minor": "16",
                "filesystem_type": null,
                "paths": [
                  "/dev/mapper/mpathq",
                  "/dev/disk/by-id/dm-name-mpathq",
                  "/dev/disk/by-id/dm-uuid-mpath-360014054e9b5031f3434c56a0746de1f",
                  "/dev/dm-16"
                ],
                "children": [],
                "mount": null
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "36001405aa1a4a2010734758a9e57c178",
          "scsi80": "SLIO-ORG ost5            aa1a4a20-1073-4758-a9e5-7c178c6ed8ef",
          "major": "8",
          "minor": "144",
          "devpath": "/devices/platform/host4/session3/target4:0:0/4:0:0:4/block/sdj",
          "size": 5368709120,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-36001405aa1a4a2010734758a9e57c178",
            "/dev/disk/by-id/wwn-0x6001405aa1a4a2010734758a9e57c178",
            "/dev/disk/by-path/ip-10.73.40.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:oss-lun-4",
            "/dev/sdj"
          ],
          "mount": null,
          "children": [
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-14",
                "serial": "36001405aa1a4a2010734758a9e57c178",
                "scsi80": "SLIO-ORG ost5            aa1a4a20-1073-4758-a9e5-7c178c6ed8ef",
                "dm_name": "mpatho",
                "size": 5368709120,
                "major": "253",
                "minor": "14",
                "filesystem_type": null,
                "paths": [
                  "/dev/mapper/mpatho",
                  "/dev/disk/by-id/dm-name-mpatho",
                  "/dev/disk/by-id/dm-uuid-mpath-36001405aa1a4a2010734758a9e57c178",
                  "/dev/dm-14"
                ],
                "children": [],
                "mount": null
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "36001405a63b61f10cbb4e229df0792d0",
          "scsi80": "SLIO-ORG ost2            a63b61f1-0cbb-4e22-9df0-792d0cf69575",
          "major": "8",
          "minor": "64",
          "devpath": "/devices/platform/host4/session3/target4:0:0/4:0:0:1/block/sde",
          "size": 5368709120,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-36001405a63b61f10cbb4e229df0792d0",
            "/dev/disk/by-id/wwn-0x6001405a63b61f10cbb4e229df0792d0",
            "/dev/disk/by-path/ip-10.73.40.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:oss-lun-1",
            "/dev/sde"
          ],
          "mount": null,
          "children": [
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-1",
                "serial": "36001405a63b61f10cbb4e229df0792d0",
                "scsi80": "SLIO-ORG ost2            a63b61f1-0cbb-4e22-9df0-792d0cf69575",
                "dm_name": "mpathb",
                "size": 5368709120,
                "major": "253",
                "minor": "1",
                "filesystem_type": null,
                "paths": [
                  "/dev/mapper/mpathb",
                  "/dev/disk/by-id/dm-name-mpathb",
                  "/dev/disk/by-id/dm-uuid-mpath-36001405a63b61f10cbb4e229df0792d0",
                  "/dev/dm-1"
                ],
                "children": [],
                "mount": null
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "360014051ea57ad4ffc243d6bcab8eb8c",
          "scsi80": "SLIO-ORG ost3            1ea57ad4-ffc2-43d6-bcab-8eb8c2a60bfb",
          "major": "8",
          "minor": "80",
          "devpath": "/devices/platform/host4/session3/target4:0:0/4:0:0:2/block/sdf",
          "size": 5368709120,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-360014051ea57ad4ffc243d6bcab8eb8c",
            "/dev/disk/by-id/wwn-0x60014051ea57ad4ffc243d6bcab8eb8c",
            "/dev/disk/by-path/ip-10.73.40.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:oss-lun-2",
            "/dev/sdf"
          ],
          "mount": null,
          "children": [
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-12",
                "serial": "360014051ea57ad4ffc243d6bcab8eb8c",
                "scsi80": "SLIO-ORG ost3            1ea57ad4-ffc2-43d6-bcab-8eb8c2a60bfb",
                "dm_name": "mpathm",
                "size": 5368709120,
                "major": "253",
                "minor": "12",
                "filesystem_type": null,
                "paths": [
                  "/dev/mapper/mpathm",
                  "/dev/disk/by-id/dm-name-mpathm",
                  "/dev/disk/by-id/dm-uuid-mpath-360014051ea57ad4ffc243d6bcab8eb8c",
                  "/dev/dm-12"
                ],
                "children": [],
                "mount": null
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "36001405b1662648389c47ae91f7f9c18",
          "scsi80": "SLIO-ORG ost20           b1662648-389c-47ae-91f7-f9c18ead9f54",
          "major": "66",
          "minor": "128",
          "devpath": "/devices/platform/host5/session4/target5:0:0/5:0:0:19/block/sdao",
          "size": 5368709120,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-36001405b1662648389c47ae91f7f9c18",
            "/dev/disk/by-id/wwn-0x6001405b1662648389c47ae91f7f9c18",
            "/dev/disk/by-path/ip-10.73.50.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:oss-lun-19",
            "/dev/sdao"
          ],
          "mount": null,
          "children": [
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-11",
                "serial": "36001405b1662648389c47ae91f7f9c18",
                "scsi80": "SLIO-ORG ost20           b1662648-389c-47ae-91f7-f9c18ead9f54",
                "dm_name": "mpathl",
                "size": 5368709120,
                "major": "253",
                "minor": "11",
                "filesystem_type": null,
                "paths": [
                  "/dev/mapper/mpathl",
                  "/dev/disk/by-id/dm-name-mpathl",
                  "/dev/disk/by-id/dm-uuid-mpath-36001405b1662648389c47ae91f7f9c18",
                  "/dev/dm-11"
                ],
                "children": [],
                "mount": null
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "360014053fe9e70a1aa8470faaa82b7b0",
          "scsi80": "SLIO-ORG ost12           3fe9e70a-1aa8-470f-aaa8-2b7b0e525b83",
          "major": "65",
          "minor": "112",
          "devpath": "/devices/platform/host4/session3/target4:0:0/4:0:0:11/block/sdx",
          "size": 5368709120,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-360014053fe9e70a1aa8470faaa82b7b0",
            "/dev/disk/by-id/wwn-0x60014053fe9e70a1aa8470faaa82b7b0",
            "/dev/disk/by-path/ip-10.73.40.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:oss-lun-11",
            "/dev/sdx"
          ],
          "mount": null,
          "children": [
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-3",
                "serial": "360014053fe9e70a1aa8470faaa82b7b0",
                "scsi80": "SLIO-ORG ost12           3fe9e70a-1aa8-470f-aaa8-2b7b0e525b83",
                "dm_name": "mpathd",
                "size": 5368709120,
                "major": "253",
                "minor": "3",
                "filesystem_type": null,
                "paths": [
                  "/dev/mapper/mpathd",
                  "/dev/disk/by-id/dm-name-mpathd",
                  "/dev/disk/by-id/dm-uuid-mpath-360014053fe9e70a1aa8470faaa82b7b0",
                  "/dev/dm-3"
                ],
                "children": [],
                "mount": null
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "36001405b1662648389c47ae91f7f9c18",
          "scsi80": "SLIO-ORG ost20           b1662648-389c-47ae-91f7-f9c18ead9f54",
          "major": "66",
          "minor": "112",
          "devpath": "/devices/platform/host4/session3/target4:0:0/4:0:0:19/block/sdan",
          "size": 5368709120,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-36001405b1662648389c47ae91f7f9c18",
            "/dev/disk/by-id/wwn-0x6001405b1662648389c47ae91f7f9c18",
            "/dev/disk/by-path/ip-10.73.40.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:oss-lun-19",
            "/dev/sdan"
          ],
          "mount": null,
          "children": [
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-11",
                "serial": "36001405b1662648389c47ae91f7f9c18",
                "scsi80": "SLIO-ORG ost20           b1662648-389c-47ae-91f7-f9c18ead9f54",
                "dm_name": "mpathl",
                "size": 5368709120,
                "major": "253",
                "minor": "11",
                "filesystem_type": null,
                "paths": [
                  "/dev/mapper/mpathl",
                  "/dev/disk/by-id/dm-name-mpathl",
                  "/dev/disk/by-id/dm-uuid-mpath-36001405b1662648389c47ae91f7f9c18",
                  "/dev/dm-11"
                ],
                "children": [],
                "mount": null
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "360014053fff9fd2761f4efe9143a33ff",
          "scsi80": "SLIO-ORG ost17           3fff9fd2-761f-4efe-9143-a33ff9ff7a52",
          "major": "66",
          "minor": "32",
          "devpath": "/devices/platform/host4/session3/target4:0:0/4:0:0:16/block/sdai",
          "size": 5368709120,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-360014053fff9fd2761f4efe9143a33ff",
            "/dev/disk/by-id/wwn-0x60014053fff9fd2761f4efe9143a33ff",
            "/dev/disk/by-path/ip-10.73.40.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:oss-lun-16",
            "/dev/sdai"
          ],
          "mount": null,
          "children": [
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-8",
                "serial": "360014053fff9fd2761f4efe9143a33ff",
                "scsi80": "SLIO-ORG ost17           3fff9fd2-761f-4efe-9143-a33ff9ff7a52",
                "dm_name": "mpathi",
                "size": 5368709120,
                "major": "253",
                "minor": "8",
                "filesystem_type": null,
                "paths": [
                  "/dev/mapper/mpathi",
                  "/dev/disk/by-id/dm-name-mpathi",
                  "/dev/disk/by-id/dm-uuid-mpath-360014053fff9fd2761f4efe9143a33ff",
                  "/dev/dm-8"
                ],
                "children": [],
                "mount": null
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "36001405047a9e1ee2c04af6b26216f3a",
          "scsi80": "SLIO-ORG ost19           047a9e1e-e2c0-4af6-b262-16f3ac3ca915",
          "major": "66",
          "minor": "96",
          "devpath": "/devices/platform/host5/session4/target5:0:0/5:0:0:18/block/sdam",
          "size": 5368709120,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-36001405047a9e1ee2c04af6b26216f3a",
            "/dev/disk/by-id/wwn-0x6001405047a9e1ee2c04af6b26216f3a",
            "/dev/disk/by-path/ip-10.73.50.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:oss-lun-18",
            "/dev/sdam"
          ],
          "mount": null,
          "children": [
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-10",
                "serial": "36001405047a9e1ee2c04af6b26216f3a",
                "scsi80": "SLIO-ORG ost19           047a9e1e-e2c0-4af6-b262-16f3ac3ca915",
                "dm_name": "mpathk",
                "size": 5368709120,
                "major": "253",
                "minor": "10",
                "filesystem_type": null,
                "paths": [
                  "/dev/mapper/mpathk",
                  "/dev/disk/by-id/dm-name-mpathk",
                  "/dev/disk/by-id/dm-uuid-mpath-36001405047a9e1ee2c04af6b26216f3a",
                  "/dev/dm-10"
                ],
                "children": [],
                "mount": null
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "36001405c525c75b8ee1471dbbb344dd8",
          "scsi80": "SLIO-ORG ost15           c525c75b-8ee1-471d-bbb3-44dd80198b3f",
          "major": "65",
          "minor": "224",
          "devpath": "/devices/platform/host5/session4/target5:0:0/5:0:0:14/block/sdae",
          "size": 5368709120,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-36001405c525c75b8ee1471dbbb344dd8",
            "/dev/disk/by-id/wwn-0x6001405c525c75b8ee1471dbbb344dd8",
            "/dev/disk/by-path/ip-10.73.50.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:oss-lun-14",
            "/dev/sdae"
          ],
          "mount": null,
          "children": [
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-6",
                "serial": "36001405c525c75b8ee1471dbbb344dd8",
                "scsi80": "SLIO-ORG ost15           c525c75b-8ee1-471d-bbb3-44dd80198b3f",
                "dm_name": "mpathg",
                "size": 5368709120,
                "major": "253",
                "minor": "6",
                "filesystem_type": "LVM2_member",
                "paths": [
                  "/dev/mapper/mpathg",
                  "/dev/disk/by-id/dm-name-mpathg",
                  "/dev/disk/by-id/dm-uuid-mpath-36001405c525c75b8ee1471dbbb344dd8",
                  "/dev/disk/by-id/lvm-pv-uuid-Y0MPay-Yimt-cJJx-ZN92-KFLT-BPJf-SjPIbO",
                  "/dev/dm-6"
                ],
                "children": [
                  {
                    "VolumeGroup": {
                      "name": "vg1",
                      "uuid": "UDIbPXrzaeBLNKim8kDOqcWfXbG2eRKt",
                      "size": 0,
                      "children": [
                        {
                          "LogicalVolume": {
                            "name": "lv1",
                            "uuid": "9rYEeS4U3eCNTgx1UovfQIXv16TTjel4",
                            "major": "253",
                            "minor": "20",
                            "size": 67108864,
                            "children": [],
                            "devpath": "/devices/virtual/block/dm-20",
                            "paths": [
                              "/dev/mapper/vg1-lv1",
                              "/dev/disk/by-id/dm-name-vg1-lv1",
                              "/dev/disk/by-id/dm-uuid-LVM-UDIbPXrzaeBLNKim8kDOqcWfXbG2eRKt9rYEeS4U3eCNTgx1UovfQIXv16TTjel4",
                              "/dev/dm-20",
                              "/dev/vg1/lv1"
                            ],
                            "filesystem_type": null,
                            "mount": null
                          }
                        }
                      ]
                    }
                  }
                ],
                "mount": null
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "3600140564eea787d99444d79c15fc577",
          "scsi80": "SLIO-ORG ost10           64eea787-d994-44d7-9c15-fc577fde7809",
          "major": "65",
          "minor": "48",
          "devpath": "/devices/platform/host4/session3/target4:0:0/4:0:0:9/block/sdt",
          "size": 5368709120,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-3600140564eea787d99444d79c15fc577",
            "/dev/disk/by-id/wwn-0x600140564eea787d99444d79c15fc577",
            "/dev/disk/by-path/ip-10.73.40.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:oss-lun-9",
            "/dev/sdt"
          ],
          "mount": null,
          "children": [
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-19",
                "serial": "3600140564eea787d99444d79c15fc577",
                "scsi80": "SLIO-ORG ost10           64eea787-d994-44d7-9c15-fc577fde7809",
                "dm_name": "mpatht",
                "size": 5368709120,
                "major": "253",
                "minor": "19",
                "filesystem_type": null,
                "paths": [
                  "/dev/mapper/mpatht",
                  "/dev/disk/by-id/dm-name-mpatht",
                  "/dev/disk/by-id/dm-uuid-mpath-3600140564eea787d99444d79c15fc577",
                  "/dev/dm-19"
                ],
                "children": [],
                "mount": null
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "36001405c9535ca96e924f9fa2e32ed89",
          "scsi80": "SLIO-ORG ost4            c9535ca9-6e92-4f9f-a2e3-2ed89e8cf8be",
          "major": "8",
          "minor": "112",
          "devpath": "/devices/platform/host4/session3/target4:0:0/4:0:0:3/block/sdh",
          "size": 5368709120,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-36001405c9535ca96e924f9fa2e32ed89",
            "/dev/disk/by-id/wwn-0x6001405c9535ca96e924f9fa2e32ed89",
            "/dev/disk/by-path/ip-10.73.40.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:oss-lun-3",
            "/dev/sdh"
          ],
          "mount": null,
          "children": [
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-13",
                "serial": "36001405c9535ca96e924f9fa2e32ed89",
                "scsi80": "SLIO-ORG ost4            c9535ca9-6e92-4f9f-a2e3-2ed89e8cf8be",
                "dm_name": "mpathn",
                "size": 5368709120,
                "major": "253",
                "minor": "13",
                "filesystem_type": null,
                "paths": [
                  "/dev/mapper/mpathn",
                  "/dev/disk/by-id/dm-name-mpathn",
                  "/dev/disk/by-id/dm-uuid-mpath-36001405c9535ca96e924f9fa2e32ed89",
                  "/dev/dm-13"
                ],
                "children": [],
                "mount": null
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "360014058a65c188c7f84052b1b1185d2",
          "scsi80": "SLIO-ORG ost6            8a65c188-c7f8-4052-b1b1-185d239005ea",
          "major": "8",
          "minor": "192",
          "devpath": "/devices/platform/host5/session4/target5:0:0/5:0:0:5/block/sdm",
          "size": 5368709120,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-360014058a65c188c7f84052b1b1185d2",
            "/dev/disk/by-id/wwn-0x60014058a65c188c7f84052b1b1185d2",
            "/dev/disk/by-path/ip-10.73.50.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:oss-lun-5",
            "/dev/sdm"
          ],
          "mount": null,
          "children": [
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-15",
                "serial": "360014058a65c188c7f84052b1b1185d2",
                "scsi80": "SLIO-ORG ost6            8a65c188-c7f8-4052-b1b1-185d239005ea",
                "dm_name": "mpathp",
                "size": 5368709120,
                "major": "253",
                "minor": "15",
                "filesystem_type": null,
                "paths": [
                  "/dev/mapper/mpathp",
                  "/dev/disk/by-id/dm-name-mpathp",
                  "/dev/disk/by-id/dm-uuid-mpath-360014058a65c188c7f84052b1b1185d2",
                  "/dev/dm-15"
                ],
                "children": [],
                "mount": null
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "360014051755d7331b404ff68ae4b6e45",
          "scsi80": "SLIO-ORG ost14           1755d733-1b40-4ff6-8ae4-b6e4568b03e3",
          "major": "65",
          "minor": "176",
          "devpath": "/devices/platform/host4/session3/target4:0:0/4:0:0:13/block/sdab",
          "size": 5368709120,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-360014051755d7331b404ff68ae4b6e45",
            "/dev/disk/by-id/wwn-0x60014051755d7331b404ff68ae4b6e45",
            "/dev/disk/by-path/ip-10.73.40.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:oss-lun-13",
            "/dev/sdab"
          ],
          "mount": null,
          "children": [
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-5",
                "serial": "360014051755d7331b404ff68ae4b6e45",
                "scsi80": "SLIO-ORG ost14           1755d733-1b40-4ff6-8ae4-b6e4568b03e3",
                "dm_name": "mpathf",
                "size": 5368709120,
                "major": "253",
                "minor": "5",
                "filesystem_type": null,
                "paths": [
                  "/dev/mapper/mpathf",
                  "/dev/disk/by-id/dm-name-mpathf",
                  "/dev/disk/by-id/dm-uuid-mpath-360014051755d7331b404ff68ae4b6e45",
                  "/dev/dm-5"
                ],
                "children": [],
                "mount": null
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "3600140564eea787d99444d79c15fc577",
          "scsi80": "SLIO-ORG ost10           64eea787-d994-44d7-9c15-fc577fde7809",
          "major": "65",
          "minor": "64",
          "devpath": "/devices/platform/host5/session4/target5:0:0/5:0:0:9/block/sdu",
          "size": 5368709120,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-3600140564eea787d99444d79c15fc577",
            "/dev/disk/by-id/wwn-0x600140564eea787d99444d79c15fc577",
            "/dev/disk/by-path/ip-10.73.50.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:oss-lun-9",
            "/dev/sdu"
          ],
          "mount": null,
          "children": [
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-19",
                "serial": "3600140564eea787d99444d79c15fc577",
                "scsi80": "SLIO-ORG ost10           64eea787-d994-44d7-9c15-fc577fde7809",
                "dm_name": "mpatht",
                "size": 5368709120,
                "major": "253",
                "minor": "19",
                "filesystem_type": null,
                "paths": [
                  "/dev/mapper/mpatht",
                  "/dev/disk/by-id/dm-name-mpatht",
                  "/dev/disk/by-id/dm-uuid-mpath-3600140564eea787d99444d79c15fc577",
                  "/dev/dm-19"
                ],
                "children": [],
                "mount": null
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "36001405139a84485b2d4ea5b4f59874c",
          "scsi80": "SLIO-ORG ost13           139a8448-5b2d-4ea5-b4f5-9874cd16127b",
          "major": "65",
          "minor": "144",
          "devpath": "/devices/platform/host4/session3/target4:0:0/4:0:0:12/block/sdz",
          "size": 5368709120,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-36001405139a84485b2d4ea5b4f59874c",
            "/dev/disk/by-id/wwn-0x6001405139a84485b2d4ea5b4f59874c",
            "/dev/disk/by-path/ip-10.73.40.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:oss-lun-12",
            "/dev/sdz"
          ],
          "mount": null,
          "children": [
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-4",
                "serial": "36001405139a84485b2d4ea5b4f59874c",
                "scsi80": "SLIO-ORG ost13           139a8448-5b2d-4ea5-b4f5-9874cd16127b",
                "dm_name": "mpathe",
                "size": 5368709120,
                "major": "253",
                "minor": "4",
                "filesystem_type": null,
                "paths": [
                  "/dev/mapper/mpathe",
                  "/dev/disk/by-id/dm-name-mpathe",
                  "/dev/disk/by-id/dm-uuid-mpath-36001405139a84485b2d4ea5b4f59874c",
                  "/dev/dm-4"
                ],
                "children": [],
                "mount": null
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "3600140547e0ffe43b3f464789f1653cc",
          "scsi80": "SLIO-ORG ost11           47e0ffe4-3b3f-4647-89f1-653cc1b7c954",
          "major": "65",
          "minor": "80",
          "devpath": "/devices/platform/host5/session4/target5:0:0/5:0:0:10/block/sdv",
          "size": 5368709120,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-3600140547e0ffe43b3f464789f1653cc",
            "/dev/disk/by-id/wwn-0x600140547e0ffe43b3f464789f1653cc",
            "/dev/disk/by-path/ip-10.73.50.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:oss-lun-10",
            "/dev/sdv"
          ],
          "mount": null,
          "children": [
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-2",
                "serial": "3600140547e0ffe43b3f464789f1653cc",
                "scsi80": "SLIO-ORG ost11           47e0ffe4-3b3f-4647-89f1-653cc1b7c954",
                "dm_name": "mpathc",
                "size": 5368709120,
                "major": "253",
                "minor": "2",
                "filesystem_type": null,
                "paths": [
                  "/dev/mapper/mpathc",
                  "/dev/disk/by-id/dm-name-mpathc",
                  "/dev/disk/by-id/dm-uuid-mpath-3600140547e0ffe43b3f464789f1653cc",
                  "/dev/dm-2"
                ],
                "children": [],
                "mount": null
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "360014051c12549d858d4562a2e178018",
          "scsi80": "SLIO-ORG ost18           1c12549d-858d-4562-a2e1-78018d748a6f",
          "major": "66",
          "minor": "48",
          "devpath": "/devices/platform/host4/session3/target4:0:0/4:0:0:17/block/sdaj",
          "size": 5368709120,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-360014051c12549d858d4562a2e178018",
            "/dev/disk/by-id/wwn-0x60014051c12549d858d4562a2e178018",
            "/dev/disk/by-path/ip-10.73.40.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:oss-lun-17",
            "/dev/sdaj"
          ],
          "mount": null,
          "children": [
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-9",
                "serial": "360014051c12549d858d4562a2e178018",
                "scsi80": "SLIO-ORG ost18           1c12549d-858d-4562-a2e1-78018d748a6f",
                "dm_name": "mpathj",
                "size": 5368709120,
                "major": "253",
                "minor": "9",
                "filesystem_type": null,
                "paths": [
                  "/dev/mapper/mpathj",
                  "/dev/disk/by-id/dm-name-mpathj",
                  "/dev/disk/by-id/dm-uuid-mpath-360014051c12549d858d4562a2e178018",
                  "/dev/dm-9"
                ],
                "children": [],
                "mount": null
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "3600140568c946040400460a896d0b196",
          "scsi80": "SLIO-ORG ost1            68c94604-0400-460a-896d-0b196cd0a235",
          "major": "8",
          "minor": "32",
          "devpath": "/devices/platform/host4/session3/target4:0:0/4:0:0:0/block/sdc",
          "size": 5368709120,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-3600140568c946040400460a896d0b196",
            "/dev/disk/by-id/wwn-0x600140568c946040400460a896d0b196",
            "/dev/disk/by-path/ip-10.73.40.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:oss-lun-0",
            "/dev/sdc"
          ],
          "mount": null,
          "children": [
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-0",
                "serial": "3600140568c946040400460a896d0b196",
                "scsi80": "SLIO-ORG ost1            68c94604-0400-460a-896d-0b196cd0a235",
                "dm_name": "mpatha",
                "size": 5368709120,
                "major": "253",
                "minor": "0",
                "filesystem_type": null,
                "paths": [
                  "/dev/mapper/mpatha",
                  "/dev/disk/by-id/dm-name-mpatha",
                  "/dev/disk/by-id/dm-uuid-mpath-3600140568c946040400460a896d0b196",
                  "/dev/dm-0"
                ],
                "children": [],
                "mount": null
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "3600140547f1dbaca8e344809057273c5",
          "scsi80": "SLIO-ORG ost8            47f1dbac-a8e3-4480-9057-273c502f4dd6",
          "major": "65",
          "minor": "0",
          "devpath": "/devices/platform/host5/session4/target5:0:0/5:0:0:7/block/sdq",
          "size": 5368709120,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-3600140547f1dbaca8e344809057273c5",
            "/dev/disk/by-id/wwn-0x600140547f1dbaca8e344809057273c5",
            "/dev/disk/by-path/ip-10.73.50.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:oss-lun-7",
            "/dev/sdq"
          ],
          "mount": null,
          "children": [
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-17",
                "serial": "3600140547f1dbaca8e344809057273c5",
                "scsi80": "SLIO-ORG ost8            47f1dbac-a8e3-4480-9057-273c502f4dd6",
                "dm_name": "mpathr",
                "size": 5368709120,
                "major": "253",
                "minor": "17",
                "filesystem_type": null,
                "paths": [
                  "/dev/mapper/mpathr",
                  "/dev/disk/by-id/dm-name-mpathr",
                  "/dev/disk/by-id/dm-uuid-mpath-3600140547f1dbaca8e344809057273c5",
                  "/dev/dm-17"
                ],
                "children": [],
                "mount": null
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "1ATA     VBOX HARDDISK                           VB289a63d7-b2394fde",
          "scsi80": "SATA     VBOX HARDDISK   VB289a63d7-b2394fde",
          "major": "8",
          "minor": "0",
          "devpath": "/devices/pci0000:00/0000:00:01.1/ata1/host0/target0:0:0/0:0:0:0/block/sda",
          "size": 42949672960,
          "filesystem_type": null,
          "paths": [
            "/dev/disk/by-id/ata-VBOX_HARDDISK_VB289a63d7-b2394fde",
            "/dev/disk/by-path/pci-0000:00:01.1-ata-1.0",
            "/dev/sda"
          ],
          "mount": null,
          "children": [
            {
              "Partition": {
                "partition_number": 1,
                "size": 42948624384,
                "major": "8",
                "minor": "1",
                "devpath": "/devices/pci0000:00/0000:00:01.1/ata1/host0/target0:0:0/0:0:0:0/block/sda/sda1",
                "filesystem_type": "xfs",
                "paths": [
                  "/dev/disk/by-id/ata-VBOX_HARDDISK_VB289a63d7-b2394fde-part1",
                  "/dev/disk/by-path/pci-0000:00:01.1-ata-1.0-part1",
                  "/dev/disk/by-uuid/f52f361a-da1a-4ea0-8c7f-ca2706e86b46",
                  "/dev/sda1"
                ],
                "mount": {
                  "source": "/dev/sda1",
                  "target": "/",
                  "fs_type": "xfs",
                  "opts": "rw,relatime,seclabel,attr2,inode64,noquota"
                },
                "children": []
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "360014053fff9fd2761f4efe9143a33ff",
          "scsi80": "SLIO-ORG ost17           3fff9fd2-761f-4efe-9143-a33ff9ff7a52",
          "major": "66",
          "minor": "16",
          "devpath": "/devices/platform/host5/session4/target5:0:0/5:0:0:16/block/sdah",
          "size": 5368709120,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-360014053fff9fd2761f4efe9143a33ff",
            "/dev/disk/by-id/wwn-0x60014053fff9fd2761f4efe9143a33ff",
            "/dev/disk/by-path/ip-10.73.50.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:oss-lun-16",
            "/dev/sdah"
          ],
          "mount": null,
          "children": [
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-8",
                "serial": "360014053fff9fd2761f4efe9143a33ff",
                "scsi80": "SLIO-ORG ost17           3fff9fd2-761f-4efe-9143-a33ff9ff7a52",
                "dm_name": "mpathi",
                "size": 5368709120,
                "major": "253",
                "minor": "8",
                "filesystem_type": null,
                "paths": [
                  "/dev/mapper/mpathi",
                  "/dev/disk/by-id/dm-name-mpathi",
                  "/dev/disk/by-id/dm-uuid-mpath-360014053fff9fd2761f4efe9143a33ff",
                  "/dev/dm-8"
                ],
                "children": [],
                "mount": null
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "360014058a65c188c7f84052b1b1185d2",
          "scsi80": "SLIO-ORG ost6            8a65c188-c7f8-4052-b1b1-185d239005ea",
          "major": "8",
          "minor": "176",
          "devpath": "/devices/platform/host4/session3/target4:0:0/4:0:0:5/block/sdl",
          "size": 5368709120,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-360014058a65c188c7f84052b1b1185d2",
            "/dev/disk/by-id/wwn-0x60014058a65c188c7f84052b1b1185d2",
            "/dev/disk/by-path/ip-10.73.40.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:oss-lun-5",
            "/dev/sdl"
          ],
          "mount": null,
          "children": [
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-15",
                "serial": "360014058a65c188c7f84052b1b1185d2",
                "scsi80": "SLIO-ORG ost6            8a65c188-c7f8-4052-b1b1-185d239005ea",
                "dm_name": "mpathp",
                "size": 5368709120,
                "major": "253",
                "minor": "15",
                "filesystem_type": null,
                "paths": [
                  "/dev/mapper/mpathp",
                  "/dev/disk/by-id/dm-name-mpathp",
                  "/dev/disk/by-id/dm-uuid-mpath-360014058a65c188c7f84052b1b1185d2",
                  "/dev/dm-15"
                ],
                "children": [],
                "mount": null
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "3600140547f1dbaca8e344809057273c5",
          "scsi80": "SLIO-ORG ost8            47f1dbac-a8e3-4480-9057-273c502f4dd6",
          "major": "8",
          "minor": "240",
          "devpath": "/devices/platform/host4/session3/target4:0:0/4:0:0:7/block/sdp",
          "size": 5368709120,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-3600140547f1dbaca8e344809057273c5",
            "/dev/disk/by-id/wwn-0x600140547f1dbaca8e344809057273c5",
            "/dev/disk/by-path/ip-10.73.40.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:oss-lun-7",
            "/dev/sdp"
          ],
          "mount": null,
          "children": [
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-17",
                "serial": "3600140547f1dbaca8e344809057273c5",
                "scsi80": "SLIO-ORG ost8            47f1dbac-a8e3-4480-9057-273c502f4dd6",
                "dm_name": "mpathr",
                "size": 5368709120,
                "major": "253",
                "minor": "17",
                "filesystem_type": null,
                "paths": [
                  "/dev/mapper/mpathr",
                  "/dev/disk/by-id/dm-name-mpathr",
                  "/dev/disk/by-id/dm-uuid-mpath-3600140547f1dbaca8e344809057273c5",
                  "/dev/dm-17"
                ],
                "children": [],
                "mount": null
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "360014053fe9e70a1aa8470faaa82b7b0",
          "scsi80": "SLIO-ORG ost12           3fe9e70a-1aa8-470f-aaa8-2b7b0e525b83",
          "major": "65",
          "minor": "128",
          "devpath": "/devices/platform/host5/session4/target5:0:0/5:0:0:11/block/sdy",
          "size": 5368709120,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-360014053fe9e70a1aa8470faaa82b7b0",
            "/dev/disk/by-id/wwn-0x60014053fe9e70a1aa8470faaa82b7b0",
            "/dev/disk/by-path/ip-10.73.50.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:oss-lun-11",
            "/dev/sdy"
          ],
          "mount": null,
          "children": [
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-3",
                "serial": "360014053fe9e70a1aa8470faaa82b7b0",
                "scsi80": "SLIO-ORG ost12           3fe9e70a-1aa8-470f-aaa8-2b7b0e525b83",
                "dm_name": "mpathd",
                "size": 5368709120,
                "major": "253",
                "minor": "3",
                "filesystem_type": null,
                "paths": [
                  "/dev/mapper/mpathd",
                  "/dev/disk/by-id/dm-name-mpathd",
                  "/dev/disk/by-id/dm-uuid-mpath-360014053fe9e70a1aa8470faaa82b7b0",
                  "/dev/dm-3"
                ],
                "children": [],
                "mount": null
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "36001405047a9e1ee2c04af6b26216f3a",
          "scsi80": "SLIO-ORG ost19           047a9e1e-e2c0-4af6-b262-16f3ac3ca915",
          "major": "66",
          "minor": "80",
          "devpath": "/devices/platform/host4/session3/target4:0:0/4:0:0:18/block/sdal",
          "size": 5368709120,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-36001405047a9e1ee2c04af6b26216f3a",
            "/dev/disk/by-id/wwn-0x6001405047a9e1ee2c04af6b26216f3a",
            "/dev/disk/by-path/ip-10.73.40.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:oss-lun-18",
            "/dev/sdal"
          ],
          "mount": null,
          "children": [
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-10",
                "serial": "36001405047a9e1ee2c04af6b26216f3a",
                "scsi80": "SLIO-ORG ost19           047a9e1e-e2c0-4af6-b262-16f3ac3ca915",
                "dm_name": "mpathk",
                "size": 5368709120,
                "major": "253",
                "minor": "10",
                "filesystem_type": null,
                "paths": [
                  "/dev/mapper/mpathk",
                  "/dev/disk/by-id/dm-name-mpathk",
                  "/dev/disk/by-id/dm-uuid-mpath-36001405047a9e1ee2c04af6b26216f3a",
                  "/dev/dm-10"
                ],
                "children": [],
                "mount": null
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "360014054e9b5031f3434c56a0746de1f",
          "scsi80": "SLIO-ORG ost7            4e9b5031-f343-4c56-a074-6de1feb8f72c",
          "major": "8",
          "minor": "208",
          "devpath": "/devices/platform/host4/session3/target4:0:0/4:0:0:6/block/sdn",
          "size": 5368709120,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-360014054e9b5031f3434c56a0746de1f",
            "/dev/disk/by-id/wwn-0x60014054e9b5031f3434c56a0746de1f",
            "/dev/disk/by-path/ip-10.73.40.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:oss-lun-6",
            "/dev/sdn"
          ],
          "mount": null,
          "children": [
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-16",
                "serial": "360014054e9b5031f3434c56a0746de1f",
                "scsi80": "SLIO-ORG ost7            4e9b5031-f343-4c56-a074-6de1feb8f72c",
                "dm_name": "mpathq",
                "size": 5368709120,
                "major": "253",
                "minor": "16",
                "filesystem_type": null,
                "paths": [
                  "/dev/mapper/mpathq",
                  "/dev/disk/by-id/dm-name-mpathq",
                  "/dev/disk/by-id/dm-uuid-mpath-360014054e9b5031f3434c56a0746de1f",
                  "/dev/dm-16"
                ],
                "children": [],
                "mount": null
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "360014051c12549d858d4562a2e178018",
          "scsi80": "SLIO-ORG ost18           1c12549d-858d-4562-a2e1-78018d748a6f",
          "major": "66",
          "minor": "64",
          "devpath": "/devices/platform/host5/session4/target5:0:0/5:0:0:17/block/sdak",
          "size": 5368709120,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-360014051c12549d858d4562a2e178018",
            "/dev/disk/by-id/wwn-0x60014051c12549d858d4562a2e178018",
            "/dev/disk/by-path/ip-10.73.50.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:oss-lun-17",
            "/dev/sdak"
          ],
          "mount": null,
          "children": [
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-9",
                "serial": "360014051c12549d858d4562a2e178018",
                "scsi80": "SLIO-ORG ost18           1c12549d-858d-4562-a2e1-78018d748a6f",
                "dm_name": "mpathj",
                "size": 5368709120,
                "major": "253",
                "minor": "9",
                "filesystem_type": null,
                "paths": [
                  "/dev/mapper/mpathj",
                  "/dev/disk/by-id/dm-name-mpathj",
                  "/dev/disk/by-id/dm-uuid-mpath-360014051c12549d858d4562a2e178018",
                  "/dev/dm-9"
                ],
                "children": [],
                "mount": null
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "36001405139a84485b2d4ea5b4f59874c",
          "scsi80": "SLIO-ORG ost13           139a8448-5b2d-4ea5-b4f5-9874cd16127b",
          "major": "65",
          "minor": "160",
          "devpath": "/devices/platform/host5/session4/target5:0:0/5:0:0:12/block/sdaa",
          "size": 5368709120,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-36001405139a84485b2d4ea5b4f59874c",
            "/dev/disk/by-id/wwn-0x6001405139a84485b2d4ea5b4f59874c",
            "/dev/disk/by-path/ip-10.73.50.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:oss-lun-12",
            "/dev/sdaa"
          ],
          "mount": null,
          "children": [
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-4",
                "serial": "36001405139a84485b2d4ea5b4f59874c",
                "scsi80": "SLIO-ORG ost13           139a8448-5b2d-4ea5-b4f5-9874cd16127b",
                "dm_name": "mpathe",
                "size": 5368709120,
                "major": "253",
                "minor": "4",
                "filesystem_type": null,
                "paths": [
                  "/dev/mapper/mpathe",
                  "/dev/disk/by-id/dm-name-mpathe",
                  "/dev/disk/by-id/dm-uuid-mpath-36001405139a84485b2d4ea5b4f59874c",
                  "/dev/dm-4"
                ],
                "children": [],
                "mount": null
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "3600140568c946040400460a896d0b196",
          "scsi80": "SLIO-ORG ost1            68c94604-0400-460a-896d-0b196cd0a235",
          "major": "8",
          "minor": "16",
          "devpath": "/devices/platform/host5/session4/target5:0:0/5:0:0:0/block/sdb",
          "size": 5368709120,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-3600140568c946040400460a896d0b196",
            "/dev/disk/by-id/wwn-0x600140568c946040400460a896d0b196",
            "/dev/disk/by-path/ip-10.73.50.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:oss-lun-0",
            "/dev/sdb"
          ],
          "mount": null,
          "children": [
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-0",
                "serial": "3600140568c946040400460a896d0b196",
                "scsi80": "SLIO-ORG ost1            68c94604-0400-460a-896d-0b196cd0a235",
                "dm_name": "mpatha",
                "size": 5368709120,
                "major": "253",
                "minor": "0",
                "filesystem_type": null,
                "paths": [
                  "/dev/mapper/mpatha",
                  "/dev/disk/by-id/dm-name-mpatha",
                  "/dev/disk/by-id/dm-uuid-mpath-3600140568c946040400460a896d0b196",
                  "/dev/dm-0"
                ],
                "children": [],
                "mount": null
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "36001405c525c75b8ee1471dbbb344dd8",
          "scsi80": "SLIO-ORG ost15           c525c75b-8ee1-471d-bbb3-44dd80198b3f",
          "major": "65",
          "minor": "208",
          "devpath": "/devices/platform/host4/session3/target4:0:0/4:0:0:14/block/sdad",
          "size": 5368709120,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-36001405c525c75b8ee1471dbbb344dd8",
            "/dev/disk/by-id/wwn-0x6001405c525c75b8ee1471dbbb344dd8",
            "/dev/disk/by-path/ip-10.73.40.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:oss-lun-14",
            "/dev/sdad"
          ],
          "mount": null,
          "children": [
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-6",
                "serial": "36001405c525c75b8ee1471dbbb344dd8",
                "scsi80": "SLIO-ORG ost15           c525c75b-8ee1-471d-bbb3-44dd80198b3f",
                "dm_name": "mpathg",
                "size": 5368709120,
                "major": "253",
                "minor": "6",
                "filesystem_type": "LVM2_member",
                "paths": [
                  "/dev/mapper/mpathg",
                  "/dev/disk/by-id/dm-name-mpathg",
                  "/dev/disk/by-id/dm-uuid-mpath-36001405c525c75b8ee1471dbbb344dd8",
                  "/dev/disk/by-id/lvm-pv-uuid-Y0MPay-Yimt-cJJx-ZN92-KFLT-BPJf-SjPIbO",
                  "/dev/dm-6"
                ],
                "children": [
                  {
                    "VolumeGroup": {
                      "name": "vg1",
                      "uuid": "UDIbPXrzaeBLNKim8kDOqcWfXbG2eRKt",
                      "size": 0,
                      "children": [
                        {
                          "LogicalVolume": {
                            "name": "lv1",
                            "uuid": "9rYEeS4U3eCNTgx1UovfQIXv16TTjel4",
                            "major": "253",
                            "minor": "20",
                            "size": 67108864,
                            "children": [],
                            "devpath": "/devices/virtual/block/dm-20",
                            "paths": [
                              "/dev/mapper/vg1-lv1",
                              "/dev/disk/by-id/dm-name-vg1-lv1",
                              "/dev/disk/by-id/dm-uuid-LVM-UDIbPXrzaeBLNKim8kDOqcWfXbG2eRKt9rYEeS4U3eCNTgx1UovfQIXv16TTjel4",
                              "/dev/dm-20",
                              "/dev/vg1/lv1"
                            ],
                            "filesystem_type": null,
                            "mount": null
                          }
                        }
                      ]
                    }
                  }
                ],
                "mount": null
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "360014051ea57ad4ffc243d6bcab8eb8c",
          "scsi80": "SLIO-ORG ost3            1ea57ad4-ffc2-43d6-bcab-8eb8c2a60bfb",
          "major": "8",
          "minor": "96",
          "devpath": "/devices/platform/host5/session4/target5:0:0/5:0:0:2/block/sdg",
          "size": 5368709120,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-360014051ea57ad4ffc243d6bcab8eb8c",
            "/dev/disk/by-id/wwn-0x60014051ea57ad4ffc243d6bcab8eb8c",
            "/dev/disk/by-path/ip-10.73.50.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:oss-lun-2",
            "/dev/sdg"
          ],
          "mount": null,
          "children": [
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-12",
                "serial": "360014051ea57ad4ffc243d6bcab8eb8c",
                "scsi80": "SLIO-ORG ost3            1ea57ad4-ffc2-43d6-bcab-8eb8c2a60bfb",
                "dm_name": "mpathm",
                "size": 5368709120,
                "major": "253",
                "minor": "12",
                "filesystem_type": null,
                "paths": [
                  "/dev/mapper/mpathm",
                  "/dev/disk/by-id/dm-name-mpathm",
                  "/dev/disk/by-id/dm-uuid-mpath-360014051ea57ad4ffc243d6bcab8eb8c",
                  "/dev/dm-12"
                ],
                "children": [],
                "mount": null
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "36001405a63b61f10cbb4e229df0792d0",
          "scsi80": "SLIO-ORG ost2            a63b61f1-0cbb-4e22-9df0-792d0cf69575",
          "major": "8",
          "minor": "48",
          "devpath": "/devices/platform/host5/session4/target5:0:0/5:0:0:1/block/sdd",
          "size": 5368709120,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-36001405a63b61f10cbb4e229df0792d0",
            "/dev/disk/by-id/wwn-0x6001405a63b61f10cbb4e229df0792d0",
            "/dev/disk/by-path/ip-10.73.50.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:oss-lun-1",
            "/dev/sdd"
          ],
          "mount": null,
          "children": [
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-1",
                "serial": "36001405a63b61f10cbb4e229df0792d0",
                "scsi80": "SLIO-ORG ost2            a63b61f1-0cbb-4e22-9df0-792d0cf69575",
                "dm_name": "mpathb",
                "size": 5368709120,
                "major": "253",
                "minor": "1",
                "filesystem_type": null,
                "paths": [
                  "/dev/mapper/mpathb",
                  "/dev/disk/by-id/dm-name-mpathb",
                  "/dev/disk/by-id/dm-uuid-mpath-36001405a63b61f10cbb4e229df0792d0",
                  "/dev/dm-1"
                ],
                "children": [],
                "mount": null
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "3600140598252aa12555428f94b6ea915",
          "scsi80": "SLIO-ORG ost16           98252aa1-2555-428f-94b6-ea915aadcd5a",
          "major": "65",
          "minor": "240",
          "devpath": "/devices/platform/host4/session3/target4:0:0/4:0:0:15/block/sdaf",
          "size": 5368709120,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-3600140598252aa12555428f94b6ea915",
            "/dev/disk/by-id/wwn-0x600140598252aa12555428f94b6ea915",
            "/dev/disk/by-path/ip-10.73.40.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:oss-lun-15",
            "/dev/sdaf"
          ],
          "mount": null,
          "children": [
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-7",
                "serial": "3600140598252aa12555428f94b6ea915",
                "scsi80": "SLIO-ORG ost16           98252aa1-2555-428f-94b6-ea915aadcd5a",
                "dm_name": "mpathh",
                "size": 5368709120,
                "major": "253",
                "minor": "7",
                "filesystem_type": "LVM2_member",
                "paths": [
                  "/dev/mapper/mpathh",
                  "/dev/disk/by-id/dm-name-mpathh",
                  "/dev/disk/by-id/dm-uuid-mpath-3600140598252aa12555428f94b6ea915",
                  "/dev/disk/by-id/lvm-pv-uuid-sSb1jT-hBLl-am3F-mc9T-2cMR-oGbb-xG0FZw",
                  "/dev/dm-7"
                ],
                "children": [],
                "mount": null
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "36001405ce127d66323a4c279ca70706a",
          "scsi80": "SLIO-ORG ost9            ce127d66-323a-4c27-9ca7-0706adf87bd6",
          "major": "65",
          "minor": "32",
          "devpath": "/devices/platform/host5/session4/target5:0:0/5:0:0:8/block/sds",
          "size": 5368709120,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-36001405ce127d66323a4c279ca70706a",
            "/dev/disk/by-id/wwn-0x6001405ce127d66323a4c279ca70706a",
            "/dev/disk/by-path/ip-10.73.50.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:oss-lun-8",
            "/dev/sds"
          ],
          "mount": null,
          "children": [
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-18",
                "serial": "36001405ce127d66323a4c279ca70706a",
                "scsi80": "SLIO-ORG ost9            ce127d66-323a-4c27-9ca7-0706adf87bd6",
                "dm_name": "mpaths",
                "size": 5368709120,
                "major": "253",
                "minor": "18",
                "filesystem_type": null,
                "paths": [
                  "/dev/mapper/mpaths",
                  "/dev/disk/by-id/dm-name-mpaths",
                  "/dev/disk/by-id/dm-uuid-mpath-36001405ce127d66323a4c279ca70706a",
                  "/dev/dm-18"
                ],
                "children": [],
                "mount": null
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "3600140547e0ffe43b3f464789f1653cc",
          "scsi80": "SLIO-ORG ost11           47e0ffe4-3b3f-4647-89f1-653cc1b7c954",
          "major": "65",
          "minor": "96",
          "devpath": "/devices/platform/host4/session3/target4:0:0/4:0:0:10/block/sdw",
          "size": 5368709120,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-3600140547e0ffe43b3f464789f1653cc",
            "/dev/disk/by-id/wwn-0x600140547e0ffe43b3f464789f1653cc",
            "/dev/disk/by-path/ip-10.73.40.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:oss-lun-10",
            "/dev/sdw"
          ],
          "mount": null,
          "children": [
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-2",
                "serial": "3600140547e0ffe43b3f464789f1653cc",
                "scsi80": "SLIO-ORG ost11           47e0ffe4-3b3f-4647-89f1-653cc1b7c954",
                "dm_name": "mpathc",
                "size": 5368709120,
                "major": "253",
                "minor": "2",
                "filesystem_type": null,
                "paths": [
                  "/dev/mapper/mpathc",
                  "/dev/disk/by-id/dm-name-mpathc",
                  "/dev/disk/by-id/dm-uuid-mpath-3600140547e0ffe43b3f464789f1653cc",
                  "/dev/dm-2"
                ],
                "children": [],
                "mount": null
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "360014051755d7331b404ff68ae4b6e45",
          "scsi80": "SLIO-ORG ost14           1755d733-1b40-4ff6-8ae4-b6e4568b03e3",
          "major": "65",
          "minor": "192",
          "devpath": "/devices/platform/host5/session4/target5:0:0/5:0:0:13/block/sdac",
          "size": 5368709120,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-360014051755d7331b404ff68ae4b6e45",
            "/dev/disk/by-id/wwn-0x60014051755d7331b404ff68ae4b6e45",
            "/dev/disk/by-path/ip-10.73.50.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:oss-lun-13",
            "/dev/sdac"
          ],
          "mount": null,
          "children": [
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-5",
                "serial": "360014051755d7331b404ff68ae4b6e45",
                "scsi80": "SLIO-ORG ost14           1755d733-1b40-4ff6-8ae4-b6e4568b03e3",
                "dm_name": "mpathf",
                "size": 5368709120,
                "major": "253",
                "minor": "5",
                "filesystem_type": null,
                "paths": [
                  "/dev/mapper/mpathf",
                  "/dev/disk/by-id/dm-name-mpathf",
                  "/dev/disk/by-id/dm-uuid-mpath-360014051755d7331b404ff68ae4b6e45",
                  "/dev/dm-5"
                ],
                "children": [],
                "mount": null
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "36001405c9535ca96e924f9fa2e32ed89",
          "scsi80": "SLIO-ORG ost4            c9535ca9-6e92-4f9f-a2e3-2ed89e8cf8be",
          "major": "8",
          "minor": "128",
          "devpath": "/devices/platform/host5/session4/target5:0:0/5:0:0:3/block/sdi",
          "size": 5368709120,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-36001405c9535ca96e924f9fa2e32ed89",
            "/dev/disk/by-id/wwn-0x6001405c9535ca96e924f9fa2e32ed89",
            "/dev/disk/by-path/ip-10.73.50.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:oss-lun-3",
            "/dev/sdi"
          ],
          "mount": null,
          "children": [
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-13",
                "serial": "36001405c9535ca96e924f9fa2e32ed89",
                "scsi80": "SLIO-ORG ost4            c9535ca9-6e92-4f9f-a2e3-2ed89e8cf8be",
                "dm_name": "mpathn",
                "size": 5368709120,
                "major": "253",
                "minor": "13",
                "filesystem_type": null,
                "paths": [
                  "/dev/mapper/mpathn",
                  "/dev/disk/by-id/dm-name-mpathn",
                  "/dev/disk/by-id/dm-uuid-mpath-36001405c9535ca96e924f9fa2e32ed89",
                  "/dev/dm-13"
                ],
                "children": [],
                "mount": null
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "36001405ce127d66323a4c279ca70706a",
          "scsi80": "SLIO-ORG ost9            ce127d66-323a-4c27-9ca7-0706adf87bd6",
          "major": "65",
          "minor": "16",
          "devpath": "/devices/platform/host4/session3/target4:0:0/4:0:0:8/block/sdr",
          "size": 5368709120,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-36001405ce127d66323a4c279ca70706a",
            "/dev/disk/by-id/wwn-0x6001405ce127d66323a4c279ca70706a",
            "/dev/disk/by-path/ip-10.73.40.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:oss-lun-8",
            "/dev/sdr"
          ],
          "mount": null,
          "children": [
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-18",
                "serial": "36001405ce127d66323a4c279ca70706a",
                "scsi80": "SLIO-ORG ost9            ce127d66-323a-4c27-9ca7-0706adf87bd6",
                "dm_name": "mpaths",
                "size": 5368709120,
                "major": "253",
                "minor": "18",
                "filesystem_type": null,
                "paths": [
                  "/dev/mapper/mpaths",
                  "/dev/disk/by-id/dm-name-mpaths",
                  "/dev/disk/by-id/dm-uuid-mpath-36001405ce127d66323a4c279ca70706a",
                  "/dev/dm-18"
                ],
                "children": [],
                "mount": null
              }
            }
          ]
        }
      }
    ]
  }
}
    "#).unwrap();

        let mut data = LinuxPluginData::default();

        devtree2linuxoutput(&device, None, &mut data);

        assert_json_snapshot!(data);
    }

    #[test]
    fn test_devtree2linuxoutput_zpool() {
        let device:Device = serde_json::from_str(r#"
      {
  "Root": {
    "children": [
      {
        "ScsiDevice": {
          "serial": "36001405943dd5f394fb4b5ba71ec818f",
          "scsi80": "SLIO-ORG mdt1            943dd5f3-94fb-4b5b-a71e-c818f04b201c",
          "major": "8",
          "minor": "64",
          "devpath": "/devices/platform/host2/session1/target2:0:0/2:0:0:1/block/sde",
          "size": 5368709120,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-36001405943dd5f394fb4b5ba71ec818f",
            "/dev/disk/by-id/wwn-0x6001405943dd5f394fb4b5ba71ec818f",
            "/dev/disk/by-path/ip-10.73.40.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:mds-lun-1",
            "/dev/mdt",
            "/dev/sde"
          ],
          "mount": null,
          "children": [
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-1",
                "serial": "36001405943dd5f394fb4b5ba71ec818f",
                "scsi80": "SLIO-ORG mdt1            943dd5f3-94fb-4b5b-a71e-c818f04b201c",
                "dm_name": "mpathb",
                "size": 5368709120,
                "major": "253",
                "minor": "1",
                "filesystem_type": "zfs_member",
                "paths": [
                  "/dev/mapper/mpathb",
                  "/dev/disk/by-id/dm-name-mpathb",
                  "/dev/disk/by-id/dm-uuid-mpath-36001405943dd5f394fb4b5ba71ec818f",
                  "/dev/disk/by-label/mds",
                  "/dev/disk/by-uuid/15259234345131681652",
                  "/dev/dm-1",
                  "/dev/mdt"
                ],
                "children": [],
                "mount": null
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "36001405ecca605408894bc2aa708a09c",
          "scsi80": "SLIO-ORG mgt1            ecca6054-0889-4bc2-aa70-8a09cd7d63a8",
          "major": "8",
          "minor": "32",
          "devpath": "/devices/platform/host3/session2/target3:0:0/3:0:0:0/block/sdc",
          "size": 536870912,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-36001405ecca605408894bc2aa708a09c",
            "/dev/disk/by-id/wwn-0x6001405ecca605408894bc2aa708a09c",
            "/dev/disk/by-path/ip-10.73.50.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:mds-lun-0",
            "/dev/mgt",
            "/dev/sdc"
          ],
          "mount": null,
          "children": [
            {
              "Zpool": {
                "guid": 3383432994541088300,
                "name": "mgs",
                "health": "ONLINE",
                "state": "ACTIVE",
                "size": 520093696,
                "vdev": {
                  "Root": {
                    "children": [
                      {
                        "Disk": {
                          "guid": 7562121608132560000,
                          "state": "ONLINE",
                          "path": "/dev/mgt",
                          "dev_id": "dm-uuid-mpath-36001405ecca605408894bc2aa708a09c",
                          "phys_path": null,
                          "whole_disk": false,
                          "is_log": false
                        }
                      }
                    ],
                    "spares": [],
                    "cache": []
                  }
                },
                "props": [],
                "children": []
              }
            },
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-0",
                "serial": "36001405ecca605408894bc2aa708a09c",
                "scsi80": "SLIO-ORG mgt1            ecca6054-0889-4bc2-aa70-8a09cd7d63a8",
                "dm_name": "mpatha",
                "size": 536870912,
                "major": "253",
                "minor": "0",
                "filesystem_type": "zfs_member",
                "paths": [
                  "/dev/mapper/mpatha",
                  "/dev/disk/by-id/dm-name-mpatha",
                  "/dev/disk/by-id/dm-uuid-mpath-36001405ecca605408894bc2aa708a09c",
                  "/dev/disk/by-label/mgs",
                  "/dev/disk/by-uuid/3383432994541088053",
                  "/dev/dm-0",
                  "/dev/mgt"
                ],
                "children": [
                  {
                    "Zpool": {
                      "guid": 3383432994541088300,
                      "name": "mgs",
                      "health": "ONLINE",
                      "state": "ACTIVE",
                      "size": 520093696,
                      "vdev": {
                        "Root": {
                          "children": [
                            {
                              "Disk": {
                                "guid": 7562121608132560000,
                                "state": "ONLINE",
                                "path": "/dev/mgt",
                                "dev_id": "dm-uuid-mpath-36001405ecca605408894bc2aa708a09c",
                                "phys_path": null,
                                "whole_disk": false,
                                "is_log": false
                              }
                            }
                          ],
                          "spares": [],
                          "cache": []
                        }
                      },
                      "props": [],
                      "children": []
                    }
                  }
                ],
                "mount": null
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "36001405943dd5f394fb4b5ba71ec818f",
          "scsi80": "SLIO-ORG mdt1            943dd5f3-94fb-4b5b-a71e-c818f04b201c",
          "major": "8",
          "minor": "48",
          "devpath": "/devices/platform/host3/session2/target3:0:0/3:0:0:1/block/sdd",
          "size": 5368709120,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-36001405943dd5f394fb4b5ba71ec818f",
            "/dev/disk/by-id/wwn-0x6001405943dd5f394fb4b5ba71ec818f",
            "/dev/disk/by-path/ip-10.73.50.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:mds-lun-1",
            "/dev/mdt",
            "/dev/sdd"
          ],
          "mount": null,
          "children": [
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-1",
                "serial": "36001405943dd5f394fb4b5ba71ec818f",
                "scsi80": "SLIO-ORG mdt1            943dd5f3-94fb-4b5b-a71e-c818f04b201c",
                "dm_name": "mpathb",
                "size": 5368709120,
                "major": "253",
                "minor": "1",
                "filesystem_type": "zfs_member",
                "paths": [
                  "/dev/mapper/mpathb",
                  "/dev/disk/by-id/dm-name-mpathb",
                  "/dev/disk/by-id/dm-uuid-mpath-36001405943dd5f394fb4b5ba71ec818f",
                  "/dev/disk/by-label/mds",
                  "/dev/disk/by-uuid/15259234345131681652",
                  "/dev/dm-1",
                  "/dev/mdt"
                ],
                "children": [],
                "mount": null
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "36001405ecca605408894bc2aa708a09c",
          "scsi80": "SLIO-ORG mgt1            ecca6054-0889-4bc2-aa70-8a09cd7d63a8",
          "major": "8",
          "minor": "16",
          "devpath": "/devices/platform/host2/session1/target2:0:0/2:0:0:0/block/sdb",
          "size": 536870912,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-36001405ecca605408894bc2aa708a09c",
            "/dev/disk/by-id/wwn-0x6001405ecca605408894bc2aa708a09c",
            "/dev/disk/by-path/ip-10.73.40.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:mds-lun-0",
            "/dev/mgt",
            "/dev/sdb"
          ],
          "mount": null,
          "children": [
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-0",
                "serial": "36001405ecca605408894bc2aa708a09c",
                "scsi80": "SLIO-ORG mgt1            ecca6054-0889-4bc2-aa70-8a09cd7d63a8",
                "dm_name": "mpatha",
                "size": 536870912,
                "major": "253",
                "minor": "0",
                "filesystem_type": "zfs_member",
                "paths": [
                  "/dev/mapper/mpatha",
                  "/dev/disk/by-id/dm-name-mpatha",
                  "/dev/disk/by-id/dm-uuid-mpath-36001405ecca605408894bc2aa708a09c",
                  "/dev/disk/by-label/mgs",
                  "/dev/disk/by-uuid/3383432994541088053",
                  "/dev/dm-0",
                  "/dev/mgt"
                ],
                "children": [
                  {
                    "Zpool": {
                      "guid": 3383432994541088300,
                      "name": "mgs",
                      "health": "ONLINE",
                      "state": "ACTIVE",
                      "size": 520093696,
                      "vdev": {
                        "Root": {
                          "children": [
                            {
                              "Disk": {
                                "guid": 7562121608132560000,
                                "state": "ONLINE",
                                "path": "/dev/mgt",
                                "dev_id": "dm-uuid-mpath-36001405ecca605408894bc2aa708a09c",
                                "phys_path": null,
                                "whole_disk": false,
                                "is_log": false
                              }
                            }
                          ],
                          "spares": [],
                          "cache": []
                        }
                      },
                      "props": [],
                      "children": []
                    }
                  }
                ],
                "mount": null
              }
            },
            {
              "Zpool": {
                "guid": 3383432994541088300,
                "name": "mgs",
                "health": "ONLINE",
                "state": "ACTIVE",
                "size": 520093696,
                "vdev": {
                  "Root": {
                    "children": [
                      {
                        "Disk": {
                          "guid": 7562121608132560000,
                          "state": "ONLINE",
                          "path": "/dev/mgt",
                          "dev_id": "dm-uuid-mpath-36001405ecca605408894bc2aa708a09c",
                          "phys_path": null,
                          "whole_disk": false,
                          "is_log": false
                        }
                      }
                    ],
                    "spares": [],
                    "cache": []
                  }
                },
                "props": [],
                "children": []
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "1ATA     VBOX HARDDISK                           VB289a63d7-b2394fde",
          "scsi80": "SATA     VBOX HARDDISK   VB289a63d7-b2394fde",
          "major": "8",
          "minor": "0",
          "devpath": "/devices/pci0000:00/0000:00:01.1/ata1/host0/target0:0:0/0:0:0:0/block/sda",
          "size": 42949672960,
          "filesystem_type": null,
          "paths": [
            "/dev/disk/by-id/ata-VBOX_HARDDISK_VB289a63d7-b2394fde",
            "/dev/disk/by-path/pci-0000:00:01.1-ata-1.0",
            "/dev/sda"
          ],
          "mount": null,
          "children": [
            {
              "Partition": {
                "partition_number": 1,
                "size": 42948624384,
                "major": "8",
                "minor": "1",
                "devpath": "/devices/pci0000:00/0000:00:01.1/ata1/host0/target0:0:0/0:0:0:0/block/sda/sda1",
                "filesystem_type": "xfs",
                "paths": [
                  "/dev/disk/by-id/ata-VBOX_HARDDISK_VB289a63d7-b2394fde-part1",
                  "/dev/disk/by-path/pci-0000:00:01.1-ata-1.0-part1",
                  "/dev/disk/by-uuid/f52f361a-da1a-4ea0-8c7f-ca2706e86b46",
                  "/dev/sda1"
                ],
                "mount": {
                  "source": "/dev/sda1",
                  "target": "/",
                  "fs_type": "xfs",
                  "opts": "rw,relatime,attr2,inode64,noquota"
                },
                "children": []
              }
            }
          ]
        }
      }
    ]
  }
}
    "#).unwrap();

        let mut data = LinuxPluginData::default();

        devtree2linuxoutput(&device, None, &mut data);

        assert_json_snapshot!(data);
    }

    #[test]
    fn test_devtree2linuxoutput_dataset() {
        let device:Device = serde_json::from_str(r#"
    {
  "Root": {
    "children": [
      {
        "ScsiDevice": {
          "serial": "36001405ecca605408894bc2aa708a09c",
          "scsi80": "SLIO-ORG mgt1            ecca6054-0889-4bc2-aa70-8a09cd7d63a8",
          "major": "8",
          "minor": "16",
          "devpath": "/devices/platform/host2/session1/target2:0:0/2:0:0:0/block/sdb",
          "size": 536870912,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-36001405ecca605408894bc2aa708a09c",
            "/dev/disk/by-id/wwn-0x6001405ecca605408894bc2aa708a09c",
            "/dev/disk/by-path/ip-10.73.40.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:mds-lun-0",
            "/dev/disk/by-label/mgs",
            "/dev/disk/by-uuid/3383432994541088053",
            "/dev/mgt",
            "/dev/sdb"
          ],
          "mount": null,
          "children": [
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-0",
                "serial": "36001405ecca605408894bc2aa708a09c",
                "scsi80": "SLIO-ORG mgt1            ecca6054-0889-4bc2-aa70-8a09cd7d63a8",
                "dm_name": "mpatha",
                "size": 536870912,
                "major": "253",
                "minor": "0",
                "filesystem_type": "zfs_member",
                "paths": [
                  "/dev/mapper/mpatha",
                  "/dev/disk/by-id/dm-name-mpatha",
                  "/dev/disk/by-id/dm-uuid-mpath-36001405ecca605408894bc2aa708a09c",
                  "/dev/disk/by-label/mgs",
                  "/dev/disk/by-uuid/3383432994541088053",
                  "/dev/dm-0",
                  "/dev/mgt"
                ],
                "children": [
                  {
                    "Zpool": {
                      "guid": 3383432994541088300,
                      "name": "mgs",
                      "health": "ONLINE",
                      "state": "ACTIVE",
                      "size": 520093696,
                      "vdev": {
                        "Root": {
                          "children": [
                            {
                              "Disk": {
                                "guid": 7562121608132560000,
                                "state": "ONLINE",
                                "path": "/dev/mgt",
                                "dev_id": "dm-uuid-mpath-36001405ecca605408894bc2aa708a09c",
                                "phys_path": null,
                                "whole_disk": false,
                                "is_log": false
                              }
                            }
                          ],
                          "spares": [],
                          "cache": []
                        }
                      },
                      "props": [],
                      "children": [
                        {
                          "Dataset": {
                            "guid": 16140917920099960924,
                            "name": "mgs/MGS",
                            "kind": "filesystem",
                            "props": [
                              {
                                "name": "name",
                                "value": "mgs/MGS"
                              },
                              {
                                "name": "type",
                                "value": "filesystem"
                              },
                              {
                                "name": "creation",
                                "value": "1558110908"
                              },
                              {
                                "name": "used",
                                "value": "24576"
                              },
                              {
                                "name": "available",
                                "value": "385734656"
                              },
                              {
                                "name": "referenced",
                                "value": "24576"
                              },
                              {
                                "name": "compressratio",
                                "value": "1.00x"
                              },
                              {
                                "name": "mounted",
                                "value": "no"
                              },
                              {
                                "name": "quota",
                                "value": "0"
                              },
                              {
                                "name": "reservation",
                                "value": "0"
                              },
                              {
                                "name": "recordsize",
                                "value": "131072"
                              },
                              {
                                "name": "mountpoint",
                                "value": "none"
                              },
                              {
                                "name": "sharenfs",
                                "value": "off"
                              },
                              {
                                "name": "checksum",
                                "value": "on"
                              },
                              {
                                "name": "compression",
                                "value": "off"
                              },
                              {
                                "name": "atime",
                                "value": "on"
                              },
                              {
                                "name": "devices",
                                "value": "on"
                              },
                              {
                                "name": "exec",
                                "value": "on"
                              },
                              {
                                "name": "setuid",
                                "value": "on"
                              },
                              {
                                "name": "readonly",
                                "value": "off"
                              },
                              {
                                "name": "zoned",
                                "value": "off"
                              },
                              {
                                "name": "snapdir",
                                "value": "hidden"
                              },
                              {
                                "name": "aclinherit",
                                "value": "restricted"
                              },
                              {
                                "name": "createtxg",
                                "value": "375"
                              },
                              {
                                "name": "canmount",
                                "value": "off"
                              },
                              {
                                "name": "xattr",
                                "value": "sa"
                              },
                              {
                                "name": "copies",
                                "value": "1"
                              },
                              {
                                "name": "version",
                                "value": "5"
                              },
                              {
                                "name": "utf8only",
                                "value": "off"
                              },
                              {
                                "name": "normalization",
                                "value": "none"
                              },
                              {
                                "name": "casesensitivity",
                                "value": "sensitive"
                              },
                              {
                                "name": "vscan",
                                "value": "off"
                              },
                              {
                                "name": "nbmand",
                                "value": "off"
                              },
                              {
                                "name": "sharesmb",
                                "value": "off"
                              },
                              {
                                "name": "refquota",
                                "value": "0"
                              },
                              {
                                "name": "refreservation",
                                "value": "0"
                              },
                              {
                                "name": "guid",
                                "value": "16140917920099960924"
                              },
                              {
                                "name": "primarycache",
                                "value": "all"
                              },
                              {
                                "name": "secondarycache",
                                "value": "all"
                              },
                              {
                                "name": "usedbysnapshots",
                                "value": "0"
                              },
                              {
                                "name": "usedbydataset",
                                "value": "24576"
                              },
                              {
                                "name": "usedbychildren",
                                "value": "0"
                              },
                              {
                                "name": "usedbyrefreservation",
                                "value": "0"
                              },
                              {
                                "name": "logbias",
                                "value": "latency"
                              },
                              {
                                "name": "dedup",
                                "value": "off"
                              },
                              {
                                "name": "mlslabel",
                                "value": "none"
                              },
                              {
                                "name": "sync",
                                "value": "standard"
                              },
                              {
                                "name": "dnodesize",
                                "value": "auto"
                              },
                              {
                                "name": "refcompressratio",
                                "value": "1.00x"
                              },
                              {
                                "name": "written",
                                "value": "24576"
                              },
                              {
                                "name": "logicalused",
                                "value": "12288"
                              },
                              {
                                "name": "logicalreferenced",
                                "value": "12288"
                              },
                              {
                                "name": "volmode",
                                "value": "default"
                              },
                              {
                                "name": "filesystem_limit",
                                "value": "18446744073709551615"
                              },
                              {
                                "name": "snapshot_limit",
                                "value": "18446744073709551615"
                              },
                              {
                                "name": "filesystem_count",
                                "value": "18446744073709551615"
                              },
                              {
                                "name": "snapshot_count",
                                "value": "18446744073709551615"
                              },
                              {
                                "name": "snapdev",
                                "value": "hidden"
                              },
                              {
                                "name": "acltype",
                                "value": "off"
                              },
                              {
                                "name": "context",
                                "value": "none"
                              },
                              {
                                "name": "fscontext",
                                "value": "none"
                              },
                              {
                                "name": "defcontext",
                                "value": "none"
                              },
                              {
                                "name": "rootcontext",
                                "value": "none"
                              },
                              {
                                "name": "relatime",
                                "value": "off"
                              },
                              {
                                "name": "redundant_metadata",
                                "value": "all"
                              },
                              {
                                "name": "overlay",
                                "value": "off"
                              },
                              {
                                "name": "lustre:svname",
                                "value": "MGS"
                              },
                              {
                                "name": "lustre:flags",
                                "value": "100"
                              },
                              {
                                "name": "lustre:index",
                                "value": "65535"
                              },
                              {
                                "name": "lustre:version",
                                "value": "1"
                              }
                            ]
                          }
                        }
                      ]
                    }
                  }
                ],
                "mount": null
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "36001405943dd5f394fb4b5ba71ec818f",
          "scsi80": "SLIO-ORG mdt1            943dd5f3-94fb-4b5b-a71e-c818f04b201c",
          "major": "8",
          "minor": "48",
          "devpath": "/devices/platform/host2/session1/target2:0:0/2:0:0:1/block/sdd",
          "size": 5368709120,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-36001405943dd5f394fb4b5ba71ec818f",
            "/dev/disk/by-id/wwn-0x6001405943dd5f394fb4b5ba71ec818f",
            "/dev/disk/by-path/ip-10.73.40.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:mds-lun-1",
            "/dev/disk/by-label/mds",
            "/dev/disk/by-uuid/15259234345131681652",
            "/dev/mdt",
            "/dev/sdd"
          ],
          "mount": null,
          "children": [
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-1",
                "serial": "36001405943dd5f394fb4b5ba71ec818f",
                "scsi80": "SLIO-ORG mdt1            943dd5f3-94fb-4b5b-a71e-c818f04b201c",
                "dm_name": "mpathb",
                "size": 5368709120,
                "major": "253",
                "minor": "1",
                "filesystem_type": "zfs_member",
                "paths": [
                  "/dev/mapper/mpathb",
                  "/dev/disk/by-id/dm-name-mpathb",
                  "/dev/disk/by-id/dm-uuid-mpath-36001405943dd5f394fb4b5ba71ec818f",
                  "/dev/disk/by-label/mds",
                  "/dev/disk/by-uuid/15259234345131681652",
                  "/dev/dm-1",
                  "/dev/mdt"
                ],
                "children": [],
                "mount": null
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "1ATA     VBOX HARDDISK                           VB289a63d7-b2394fde",
          "scsi80": "SATA     VBOX HARDDISK   VB289a63d7-b2394fde",
          "major": "8",
          "minor": "0",
          "devpath": "/devices/pci0000:00/0000:00:01.1/ata1/host0/target0:0:0/0:0:0:0/block/sda",
          "size": 42949672960,
          "filesystem_type": null,
          "paths": [
            "/dev/disk/by-id/ata-VBOX_HARDDISK_VB289a63d7-b2394fde",
            "/dev/disk/by-path/pci-0000:00:01.1-ata-1.0",
            "/dev/sda"
          ],
          "mount": null,
          "children": [
            {
              "Partition": {
                "partition_number": 1,
                "size": 42948624384,
                "major": "8",
                "minor": "1",
                "devpath": "/devices/pci0000:00/0000:00:01.1/ata1/host0/target0:0:0/0:0:0:0/block/sda/sda1",
                "filesystem_type": "xfs",
                "paths": [
                  "/dev/disk/by-id/ata-VBOX_HARDDISK_VB289a63d7-b2394fde-part1",
                  "/dev/disk/by-path/pci-0000:00:01.1-ata-1.0-part1",
                  "/dev/disk/by-uuid/f52f361a-da1a-4ea0-8c7f-ca2706e86b46",
                  "/dev/sda1"
                ],
                "mount": {
                  "source": "/dev/sda1",
                  "target": "/",
                  "fs_type": "xfs",
                  "opts": "rw,relatime,attr2,inode64,noquota"
                },
                "children": []
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "36001405ecca605408894bc2aa708a09c",
          "scsi80": "SLIO-ORG mgt1            ecca6054-0889-4bc2-aa70-8a09cd7d63a8",
          "major": "8",
          "minor": "32",
          "devpath": "/devices/platform/host3/session2/target3:0:0/3:0:0:0/block/sdc",
          "size": 536870912,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-36001405ecca605408894bc2aa708a09c",
            "/dev/disk/by-id/wwn-0x6001405ecca605408894bc2aa708a09c",
            "/dev/disk/by-path/ip-10.73.50.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:mds-lun-0",
            "/dev/disk/by-label/mgs",
            "/dev/disk/by-uuid/3383432994541088053",
            "/dev/mgt",
            "/dev/sdc"
          ],
          "mount": null,
          "children": [
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-0",
                "serial": "36001405ecca605408894bc2aa708a09c",
                "scsi80": "SLIO-ORG mgt1            ecca6054-0889-4bc2-aa70-8a09cd7d63a8",
                "dm_name": "mpatha",
                "size": 536870912,
                "major": "253",
                "minor": "0",
                "filesystem_type": "zfs_member",
                "paths": [
                  "/dev/mapper/mpatha",
                  "/dev/disk/by-id/dm-name-mpatha",
                  "/dev/disk/by-id/dm-uuid-mpath-36001405ecca605408894bc2aa708a09c",
                  "/dev/disk/by-label/mgs",
                  "/dev/disk/by-uuid/3383432994541088053",
                  "/dev/dm-0",
                  "/dev/mgt"
                ],
                "children": [
                  {
                    "Zpool": {
                      "guid": 3383432994541088300,
                      "name": "mgs",
                      "health": "ONLINE",
                      "state": "ACTIVE",
                      "size": 520093696,
                      "vdev": {
                        "Root": {
                          "children": [
                            {
                              "Disk": {
                                "guid": 7562121608132560000,
                                "state": "ONLINE",
                                "path": "/dev/mgt",
                                "dev_id": "dm-uuid-mpath-36001405ecca605408894bc2aa708a09c",
                                "phys_path": null,
                                "whole_disk": false,
                                "is_log": false
                              }
                            }
                          ],
                          "spares": [],
                          "cache": []
                        }
                      },
                      "props": [],
                      "children": [
                        {
                          "Dataset": {
                            "guid": 16140917920099960924,
                            "name": "mgs/MGS",
                            "kind": "filesystem",
                            "props": [
                              {
                                "name": "name",
                                "value": "mgs/MGS"
                              },
                              {
                                "name": "type",
                                "value": "filesystem"
                              },
                              {
                                "name": "creation",
                                "value": "1558110908"
                              },
                              {
                                "name": "used",
                                "value": "24576"
                              },
                              {
                                "name": "available",
                                "value": "385734656"
                              },
                              {
                                "name": "referenced",
                                "value": "24576"
                              },
                              {
                                "name": "compressratio",
                                "value": "1.00x"
                              },
                              {
                                "name": "mounted",
                                "value": "no"
                              },
                              {
                                "name": "quota",
                                "value": "0"
                              },
                              {
                                "name": "reservation",
                                "value": "0"
                              },
                              {
                                "name": "recordsize",
                                "value": "131072"
                              },
                              {
                                "name": "mountpoint",
                                "value": "none"
                              },
                              {
                                "name": "sharenfs",
                                "value": "off"
                              },
                              {
                                "name": "checksum",
                                "value": "on"
                              },
                              {
                                "name": "compression",
                                "value": "off"
                              },
                              {
                                "name": "atime",
                                "value": "on"
                              },
                              {
                                "name": "devices",
                                "value": "on"
                              },
                              {
                                "name": "exec",
                                "value": "on"
                              },
                              {
                                "name": "setuid",
                                "value": "on"
                              },
                              {
                                "name": "readonly",
                                "value": "off"
                              },
                              {
                                "name": "zoned",
                                "value": "off"
                              },
                              {
                                "name": "snapdir",
                                "value": "hidden"
                              },
                              {
                                "name": "aclinherit",
                                "value": "restricted"
                              },
                              {
                                "name": "createtxg",
                                "value": "375"
                              },
                              {
                                "name": "canmount",
                                "value": "off"
                              },
                              {
                                "name": "xattr",
                                "value": "sa"
                              },
                              {
                                "name": "copies",
                                "value": "1"
                              },
                              {
                                "name": "version",
                                "value": "5"
                              },
                              {
                                "name": "utf8only",
                                "value": "off"
                              },
                              {
                                "name": "normalization",
                                "value": "none"
                              },
                              {
                                "name": "casesensitivity",
                                "value": "sensitive"
                              },
                              {
                                "name": "vscan",
                                "value": "off"
                              },
                              {
                                "name": "nbmand",
                                "value": "off"
                              },
                              {
                                "name": "sharesmb",
                                "value": "off"
                              },
                              {
                                "name": "refquota",
                                "value": "0"
                              },
                              {
                                "name": "refreservation",
                                "value": "0"
                              },
                              {
                                "name": "guid",
                                "value": "16140917920099960924"
                              },
                              {
                                "name": "primarycache",
                                "value": "all"
                              },
                              {
                                "name": "secondarycache",
                                "value": "all"
                              },
                              {
                                "name": "usedbysnapshots",
                                "value": "0"
                              },
                              {
                                "name": "usedbydataset",
                                "value": "24576"
                              },
                              {
                                "name": "usedbychildren",
                                "value": "0"
                              },
                              {
                                "name": "usedbyrefreservation",
                                "value": "0"
                              },
                              {
                                "name": "logbias",
                                "value": "latency"
                              },
                              {
                                "name": "dedup",
                                "value": "off"
                              },
                              {
                                "name": "mlslabel",
                                "value": "none"
                              },
                              {
                                "name": "sync",
                                "value": "standard"
                              },
                              {
                                "name": "dnodesize",
                                "value": "auto"
                              },
                              {
                                "name": "refcompressratio",
                                "value": "1.00x"
                              },
                              {
                                "name": "written",
                                "value": "24576"
                              },
                              {
                                "name": "logicalused",
                                "value": "12288"
                              },
                              {
                                "name": "logicalreferenced",
                                "value": "12288"
                              },
                              {
                                "name": "volmode",
                                "value": "default"
                              },
                              {
                                "name": "filesystem_limit",
                                "value": "18446744073709551615"
                              },
                              {
                                "name": "snapshot_limit",
                                "value": "18446744073709551615"
                              },
                              {
                                "name": "filesystem_count",
                                "value": "18446744073709551615"
                              },
                              {
                                "name": "snapshot_count",
                                "value": "18446744073709551615"
                              },
                              {
                                "name": "snapdev",
                                "value": "hidden"
                              },
                              {
                                "name": "acltype",
                                "value": "off"
                              },
                              {
                                "name": "context",
                                "value": "none"
                              },
                              {
                                "name": "fscontext",
                                "value": "none"
                              },
                              {
                                "name": "defcontext",
                                "value": "none"
                              },
                              {
                                "name": "rootcontext",
                                "value": "none"
                              },
                              {
                                "name": "relatime",
                                "value": "off"
                              },
                              {
                                "name": "redundant_metadata",
                                "value": "all"
                              },
                              {
                                "name": "overlay",
                                "value": "off"
                              },
                              {
                                "name": "lustre:svname",
                                "value": "MGS"
                              },
                              {
                                "name": "lustre:flags",
                                "value": "100"
                              },
                              {
                                "name": "lustre:index",
                                "value": "65535"
                              },
                              {
                                "name": "lustre:version",
                                "value": "1"
                              }
                            ]
                          }
                        }
                      ]
                    }
                  }
                ],
                "mount": null
              }
            }
          ]
        }
      },
      {
        "ScsiDevice": {
          "serial": "36001405943dd5f394fb4b5ba71ec818f",
          "scsi80": "SLIO-ORG mdt1            943dd5f3-94fb-4b5b-a71e-c818f04b201c",
          "major": "8",
          "minor": "64",
          "devpath": "/devices/platform/host3/session2/target3:0:0/3:0:0:1/block/sde",
          "size": 5368709120,
          "filesystem_type": "mpath_member",
          "paths": [
            "/dev/disk/by-id/scsi-36001405943dd5f394fb4b5ba71ec818f",
            "/dev/disk/by-id/wwn-0x6001405943dd5f394fb4b5ba71ec818f",
            "/dev/disk/by-path/ip-10.73.50.10:3260-iscsi-iqn.2015-01.com.whamcloud.lu:mds-lun-1",
            "/dev/disk/by-label/mds",
            "/dev/disk/by-uuid/15259234345131681652",
            "/dev/mdt",
            "/dev/sde"
          ],
          "mount": null,
          "children": [
            {
              "Mpath": {
                "devpath": "/devices/virtual/block/dm-1",
                "serial": "36001405943dd5f394fb4b5ba71ec818f",
                "scsi80": "SLIO-ORG mdt1            943dd5f3-94fb-4b5b-a71e-c818f04b201c",
                "dm_name": "mpathb",
                "size": 5368709120,
                "major": "253",
                "minor": "1",
                "filesystem_type": "zfs_member",
                "paths": [
                  "/dev/mapper/mpathb",
                  "/dev/disk/by-id/dm-name-mpathb",
                  "/dev/disk/by-id/dm-uuid-mpath-36001405943dd5f394fb4b5ba71ec818f",
                  "/dev/disk/by-label/mds",
                  "/dev/disk/by-uuid/15259234345131681652",
                  "/dev/dm-1",
                  "/dev/mdt"
                ],
                "children": [],
                "mount": null
              }
            }
          ]
        }
      }
    ]
  }
}
    "#).unwrap();

        let mut data = LinuxPluginData::default();

        devtree2linuxoutput(&device, None, &mut data);

        assert_json_snapshot!(data);
    }
}
