// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use device_types::{
    devices::{Device, LogicalVolume, MdRaid, Mpath, Partition, Root, ScsiDevice, VolumeGroup},
    mount::{FsType, Mount, MountPoint},
    DevicePath,
};
use emf_wire_types::Fqdn;
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

#[derive(Debug, Clone, serde::Serialize)]
#[serde(untagged)]
pub enum LinuxPluginItem<'a> {
    LinuxPluginDevice(LinuxPluginDevice<'a>),
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
}

impl<'a> Default for LinuxPluginData<'a> {
    fn default() -> LinuxPluginData<'a> {
        LinuxPluginData {
            devs: BTreeMap::new(),
            local_fs: BTreeMap::new(),
            mpath: BTreeMap::new(),
            vgs: BTreeMap::new(),
            lvs: BTreeMap::new(),
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
            // https://github.com/whamcloud/exascaler-management-framework/blob/841567bb99edde5b635fb1573a6485f6eb75428a/chroma_core/plugins/linux.py#L439
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
            // https://github.com/whamcloud/exascaler-management-framework/blob/841567bb99edde5b635fb1573a6485f6eb75428a/chroma_core/plugins/linux.py#L439
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

fn add_mount<'a>(
    mount: &'a Mount,
    d: &LinuxPluginDevice<'a>,
    linux_plugin_data: &mut LinuxPluginData<'a>,
) {
    // This check is working around one cause of https://github.com/whamcloud/exascaler-management-framework/issues/895
    // Once we persist device-scanner input directly in the EMF database, we won't need this fn anymore,
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
        _ => {}
    };
}

pub fn build_device_lookup<'a>(
    dev_tree: &'a Device,
    path_map: &mut BTreeMap<&'a DevicePath, MajorMinor>,
) {
    match dev_tree {
        Device::Root(Root { children }) | Device::VolumeGroup(VolumeGroup { children, .. }) => {
            for c in children {
                build_device_lookup(c, path_map);
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
                build_device_lookup(c, path_map);
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
                build_device_lookup(c, path_map);
            }
        }
    }
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
        let device: Device =
            serde_json::from_slice(include_bytes!("../fixtures/devtree.json")).unwrap();

        let mut data = LinuxPluginData::default();

        devtree2linuxoutput(&device, None, &mut data);

        assert_json_snapshot!(data);
    }
}
