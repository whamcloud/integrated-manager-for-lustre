// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{mount, DevicePath};
use im::{ordset, OrdSet};
use std::path::PathBuf;

type Children = OrdSet<Device>;
pub type Paths = OrdSet<DevicePath>;

#[derive(
    Debug, PartialEq, Eq, PartialOrd, Ord, Hash, serde::Serialize, serde::Deserialize, Clone,
)]
pub struct Root {
    pub children: Children,
}

impl Default for Root {
    fn default() -> Self {
        Self {
            children: ordset![],
        }
    }
}

#[derive(
    Debug, PartialEq, Eq, PartialOrd, Ord, Hash, serde::Serialize, serde::Deserialize, Clone,
)]
pub struct ScsiDevice {
    pub serial: Option<String>,
    pub scsi80: Option<String>,
    pub major: String,
    pub minor: String,
    pub devpath: PathBuf,
    pub size: u64,
    pub filesystem_type: Option<String>,
    pub fs_uuid: Option<String>,
    pub fs_label: Option<String>,
    pub paths: Paths,
    pub mount: Option<mount::Mount>,
    pub children: Children,
}

#[derive(
    Debug, PartialEq, Eq, PartialOrd, Ord, Hash, serde::Serialize, serde::Deserialize, Clone,
)]
pub struct Partition {
    pub serial: Option<String>,
    pub scsi80: Option<String>,
    pub partition_number: u64,
    pub size: u64,
    pub major: String,
    pub minor: String,
    pub devpath: PathBuf,
    pub filesystem_type: Option<String>,
    pub fs_uuid: Option<String>,
    pub fs_label: Option<String>,
    pub paths: Paths,
    pub mount: Option<mount::Mount>,
    pub children: Children,
}

#[derive(
    Debug, PartialEq, Eq, PartialOrd, Ord, Hash, serde::Serialize, serde::Deserialize, Clone,
)]
pub struct MdRaid {
    pub size: u64,
    pub major: String,
    pub minor: String,
    pub filesystem_type: Option<String>,
    pub fs_uuid: Option<String>,
    pub fs_label: Option<String>,
    pub paths: Paths,
    pub mount: Option<mount::Mount>,
    pub uuid: String,
    pub children: Children,
}

#[derive(
    Debug, PartialEq, Eq, PartialOrd, Ord, Hash, serde::Serialize, serde::Deserialize, Clone,
)]
pub struct Mpath {
    pub devpath: PathBuf,
    pub serial: Option<String>,
    pub scsi80: Option<String>,
    pub dm_name: String,
    pub size: u64,
    pub major: String,
    pub minor: String,
    pub filesystem_type: Option<String>,
    pub fs_uuid: Option<String>,
    pub fs_label: Option<String>,
    pub paths: Paths,
    pub children: Children,
    pub mount: Option<mount::Mount>,
}

#[derive(
    Debug, PartialEq, Eq, PartialOrd, Ord, Hash, serde::Serialize, serde::Deserialize, Clone,
)]
pub struct VolumeGroup {
    pub name: String,
    pub uuid: String,
    pub size: u64,
    pub children: Children,
}

#[derive(
    Debug, PartialEq, Eq, PartialOrd, Ord, Hash, serde::Serialize, serde::Deserialize, Clone,
)]
pub struct LogicalVolume {
    pub name: String,
    pub uuid: String,
    pub major: String,
    pub minor: String,
    pub size: u64,
    pub children: Children,
    pub devpath: PathBuf,
    pub paths: Paths,
    pub filesystem_type: Option<String>,
    pub fs_uuid: Option<String>,
    pub fs_label: Option<String>,
    pub mount: Option<mount::Mount>,
}

#[derive(
    Debug, PartialEq, Eq, PartialOrd, Ord, Hash, serde::Serialize, serde::Deserialize, Clone,
)]
pub enum Device {
    Root(Root),
    ScsiDevice(ScsiDevice),
    Partition(Partition),
    MdRaid(MdRaid),
    Mpath(Mpath),
    VolumeGroup(VolumeGroup),
    LogicalVolume(LogicalVolume),
}

#[derive(Debug, serde::Serialize, Eq, PartialEq, Ord, PartialOrd, Clone, Hash)]
pub struct DeviceId(pub String);

impl Device {
    pub fn find_device_by_devpath(&self, dev_path: &DevicePath) -> Option<&Device> {
        match self {
            Self::Root(x) => x
                .children
                .iter()
                .find_map(|c| c.find_device_by_devpath(dev_path)),
            Self::ScsiDevice(x) => {
                if x.paths.contains(dev_path) {
                    return Some(self);
                }

                x.children
                    .iter()
                    .find_map(|c| c.find_device_by_devpath(dev_path))
            }
            Self::Partition(x) => {
                if x.paths.contains(dev_path) {
                    return Some(self);
                }

                x.children
                    .iter()
                    .find_map(|c| c.find_device_by_devpath(dev_path))
            }
            Self::MdRaid(x) => {
                if x.paths.contains(dev_path) {
                    return Some(self);
                }

                x.children
                    .iter()
                    .find_map(|c| c.find_device_by_devpath(dev_path))
            }
            Self::Mpath(x) => {
                if x.paths.contains(dev_path) {
                    return Some(self);
                }

                x.children
                    .iter()
                    .find_map(|c| c.find_device_by_devpath(dev_path))
            }
            Self::VolumeGroup(x) => x
                .children
                .iter()
                .find_map(|c| c.find_device_by_devpath(dev_path)),
            Self::LogicalVolume(x) => {
                if x.paths.contains(dev_path) {
                    return Some(self);
                }

                x.children
                    .iter()
                    .find_map(|c| c.find_device_by_devpath(dev_path))
            }
        }
    }
    pub fn get_fs_uuid(&self) -> Option<&str> {
        match self {
            Self::Root(_) => None,
            Self::ScsiDevice(x) => x.fs_uuid.as_deref(),
            Self::Partition(x) => x.fs_uuid.as_deref(),
            Self::MdRaid(x) => x.fs_uuid.as_deref(),
            Self::Mpath(x) => x.fs_uuid.as_deref(),
            Self::VolumeGroup(_) => None,
            Self::LogicalVolume(x) => x.fs_uuid.as_deref(),
        }
    }
    pub fn find_device_by_id(&self, id: &DeviceId) -> Option<&Device> {
        match self {
            Self::Root(x) => x.children.iter().find_map(|c| c.find_device_by_id(id)),
            Self::ScsiDevice(x) => {
                if self.get_id().as_ref()? == id {
                    return Some(self);
                }

                x.children.iter().find_map(|c| c.find_device_by_id(id))
            }
            Self::Partition(x) => {
                if self.get_id().as_ref()? == id {
                    return Some(self);
                }

                x.children.iter().find_map(|c| c.find_device_by_id(id))
            }
            Self::MdRaid(x) => {
                if self.get_id().as_ref()? == id {
                    return Some(self);
                }

                x.children.iter().find_map(|c| c.find_device_by_id(id))
            }
            Self::Mpath(x) => {
                if self.get_id().as_ref()? == id {
                    return Some(self);
                }

                x.children.iter().find_map(|c| c.find_device_by_id(id))
            }
            Self::VolumeGroup(x) => {
                if self.get_id().as_ref()? == id {
                    return Some(self);
                }

                x.children.iter().find_map(|c| c.find_device_by_id(id))
            }
            Self::LogicalVolume(x) => {
                if self.get_id().as_ref()? == id {
                    return Some(self);
                }

                x.children.iter().find_map(|c| c.find_device_by_id(id))
            }
        }
    }
    pub fn get_id(&self) -> Option<DeviceId> {
        match self {
            Self::Root(_) => Some(DeviceId("root".into())),
            Self::ScsiDevice(x) => Some(DeviceId(format!("scsi_{}", x.serial.as_ref()?))),
            Self::Partition(x) => Some(DeviceId(format!(
                "partition{}_{}",
                x.partition_number,
                x.serial.as_ref()?
            ))),
            Self::MdRaid(x) => Some(DeviceId(format!("mdraid_{}", x.uuid))),
            Self::Mpath(x) => Some(DeviceId(format!("mpath_{}", x.serial.as_ref()?))),
            Self::VolumeGroup(x) => Some(DeviceId(format!("vg_{}", x.uuid))),
            Self::LogicalVolume(x) => Some(DeviceId(format!("lv_{}", x.uuid))),
        }
    }
    pub fn children(&self) -> Option<&OrdSet<Device>> {
        match self {
            Self::Root(x) => Some(&x.children),
            Self::ScsiDevice(x) => Some(&x.children),
            Self::Partition(x) => Some(&x.children),
            Self::MdRaid(x) => Some(&x.children),
            Self::Mpath(x) => Some(&x.children),
            Self::VolumeGroup(x) => Some(&x.children),
            Self::LogicalVolume(x) => Some(&x.children),
        }
    }
}
