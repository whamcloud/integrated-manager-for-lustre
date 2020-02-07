// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use device_types::devices::{
    self, Dataset, LogicalVolume, Mpath, Partition, Root, ScsiDevice, VolumeGroup, Zpool,
};
use std::convert::TryFrom;
use std::{
    collections::{BTreeMap, BTreeSet},
    path::Path,
};

/// A device (Block or Virtual).
/// These should be unique per cluster
#[derive(Debug, serde::Serialize)]
pub struct FlatDevice<'a> {
    pub id: DeviceId,
    pub size: u64,
    pub device_type: DeviceType,
    pub parents: BTreeSet<DeviceId>,
    pub children: BTreeSet<DeviceId>,
    pub paths: BTreeSet<&'a Path>,
    pub mount_path: Option<&'a Path>,
    pub fs_type: Option<&'a String>,
    pub fs_label: Option<&'a String>,
    pub fs_uuid: Option<&'a String>,
}

impl<'a> TryFrom<&'a ScsiDevice> for FlatDevice<'a> {
    type Error = DeviceError;

    fn try_from(x: &'a ScsiDevice) -> Result<Self, Self::Error> {
        Ok(FlatDevice {
            id: x.try_into_id()?,
            size: x.size,
            device_type: x.device_type(),
            parents: BTreeSet::new(),
            children: x
                .children
                .iter()
                .filter_map(|x| x.try_into_id().ok())
                .collect(),
            paths: x.paths.iter().map(|x| x.0.as_path()).collect(),
            mount_path: x.mount.as_ref().map(|x| x.target.0.as_path()),
            fs_type: x.filesystem_type.as_ref(),
            fs_label: x.fs_label.as_ref(),
            fs_uuid: x.fs_uuid.as_ref(),
        })
    }
}

impl<'a> TryFrom<&'a Partition> for FlatDevice<'a> {
    type Error = DeviceError;

    fn try_from(x: &'a Partition) -> Result<Self, Self::Error> {
        Ok(FlatDevice {
            id: x.try_into_id()?,
            size: x.size,
            device_type: x.device_type(),
            parents: BTreeSet::new(),
            children: x
                .children
                .iter()
                .filter_map(|x| x.try_into_id().ok())
                .collect(),
            paths: x.paths.iter().map(|x| x.0.as_path()).collect(),
            mount_path: x.mount.as_ref().map(|x| x.target.0.as_path()),
            fs_type: x.filesystem_type.as_ref(),
            fs_label: x.fs_label.as_ref(),
            fs_uuid: x.fs_uuid.as_ref(),
        })
    }
}

impl<'a> TryFrom<&'a Mpath> for FlatDevice<'a> {
    type Error = DeviceError;

    fn try_from(x: &'a Mpath) -> Result<Self, Self::Error> {
        Ok(FlatDevice {
            id: x.try_into_id()?,
            size: x.size,
            device_type: x.device_type(),
            parents: BTreeSet::new(),
            children: x
                .children
                .iter()
                .filter_map(|x| x.try_into_id().ok())
                .collect(),
            paths: x.paths.iter().map(|x| x.0.as_path()).collect(),
            mount_path: x.mount.as_ref().map(|x| x.target.0.as_path()),
            fs_type: x.filesystem_type.as_ref(),
            fs_label: x.fs_label.as_ref(),
            fs_uuid: x.fs_uuid.as_ref(),
        })
    }
}

impl<'a> TryFrom<&'a VolumeGroup> for FlatDevice<'a> {
    type Error = DeviceError;

    fn try_from(x: &'a VolumeGroup) -> Result<Self, Self::Error> {
        Ok(FlatDevice {
            id: x.try_into_id()?,
            size: x.size,
            device_type: x.device_type(),
            parents: BTreeSet::new(),
            children: x
                .children
                .iter()
                .filter_map(|x| x.try_into_id().ok())
                .collect(),
            paths: BTreeSet::new(),
            mount_path: None,
            fs_type: None,
            fs_label: None,
            fs_uuid: None,
        })
    }
}

impl<'a> TryFrom<&'a LogicalVolume> for FlatDevice<'a> {
    type Error = DeviceError;

    fn try_from(x: &'a LogicalVolume) -> Result<Self, Self::Error> {
        Ok(FlatDevice {
            id: x.try_into_id()?,
            size: x.size,
            device_type: x.device_type(),
            parents: BTreeSet::new(),
            children: x
                .children
                .iter()
                .filter_map(|x| x.try_into_id().ok())
                .collect(),
            paths: x.paths.iter().map(|x| x.0.as_path()).collect(),
            mount_path: x.mount.as_ref().map(|x| x.target.0.as_path()),
            fs_type: x.filesystem_type.as_ref(),
            fs_label: None,
            fs_uuid: None,
        })
    }
}

impl<'a> TryFrom<&'a Zpool> for FlatDevice<'a> {
    type Error = DeviceError;

    fn try_from(x: &'a Zpool) -> Result<Self, Self::Error> {
        let mut paths = BTreeSet::new();
        paths.insert(Path::new(&x.name));

        Ok(FlatDevice {
            id: x.try_into_id()?,
            size: x.size,
            device_type: x.device_type(),
            parents: BTreeSet::new(),
            children: x
                .children
                .iter()
                .filter_map(|x| x.try_into_id().ok())
                .collect(),
            paths,
            mount_path: x.mount.as_ref().map(|x| x.target.0.as_path()),
            fs_type: x.mount.as_ref().map(|x| &x.fs_type.0),
            fs_label: None,
            fs_uuid: None,
        })
    }
}

impl<'a> TryFrom<&'a Dataset> for FlatDevice<'a> {
    type Error = DeviceError;

    fn try_from(x: &'a Dataset) -> Result<Self, Self::Error> {
        let mut paths = BTreeSet::new();
        paths.insert(Path::new(&x.name));

        Ok(FlatDevice {
            id: x.try_into_id()?,
            size: 0,
            device_type: x.device_type(),
            parents: BTreeSet::new(),
            children: BTreeSet::new(),
            paths,
            mount_path: x.mount.as_ref().map(|x| x.target.0.as_path()),
            fs_type: x.mount.as_ref().map(|x| &x.fs_type.0),
            fs_label: None,
            fs_uuid: None,
        })
    }
}

fn convert_paths<'a>(xs: &'a device_types::devices::Paths) -> BTreeSet<&'a Path> {
    xs.iter().map(|x| x.0.as_path()).collect()
}

pub type FlatDevices<'a> = BTreeMap<DeviceId, FlatDevice<'a>>;

pub fn process_tree<'a>(
    tree: &'a devices::Device,
    parent_id: Option<DeviceId>,
    ds: &mut FlatDevices<'a>,
) {
    match tree {
        devices::Device::Root(Root { children }) => {
            for c in children {
                process_tree(c, None, ds)
            }
        }
        devices::Device::ScsiDevice(x) => match FlatDevice::try_from(x) {
            Ok(device) => {
                let id = device.id.clone();

                ds.entry(device.id.clone())
                    .and_modify(|d| {
                        d.fs_uuid = d.fs_uuid.or(x.fs_uuid.as_ref());
                        d.fs_label = d.fs_label.or(x.fs_label.as_ref());

                        d.paths.extend(convert_paths(&x.paths).iter())
                    })
                    .or_insert(device);

                for c in x.children.iter() {
                    process_tree(c, Some(id.clone()), ds)
                }
            }
            Err(e) => tracing::warn!("discarding ScsiDevice {:?} due to error {}", x, e),
        },
        devices::Device::Partition(x) => match FlatDevice::try_from(x) {
            Ok(device) => {
                let id = device.id.clone();

                let device = ds
                    .entry(device.id.clone())
                    .and_modify(|d| d.paths.extend(convert_paths(&x.paths).iter()))
                    .or_insert(device);

                if let Some(p) = parent_id {
                    device.parents.insert(p);
                }

                for c in x.children.iter() {
                    process_tree(c, Some(id.clone()), ds)
                }
            }
            Err(e) => tracing::warn!("discarding Partition {:?} due to error {}", x, e),
        },
        devices::Device::MdRaid(x) => {
            tracing::error!("discarding MdRaid {:?} because it's not implemented", x)
        }
        devices::Device::Mpath(x) => match FlatDevice::try_from(x) {
            Ok(device) => {
                let id = device.id.clone();

                let device = ds
                    .entry(device.id.clone())
                    .and_modify(|d| d.paths.extend(convert_paths(&x.paths).iter()))
                    .or_insert(device);

                if let Some(p) = parent_id {
                    device.parents.insert(p);
                }

                for c in x.children.iter() {
                    process_tree(c, Some(id.clone()), ds)
                }
            }
            Err(e) => tracing::warn!("discarding Mpath {:?} due to error {}", x, e),
        },
        devices::Device::VolumeGroup(x) => match FlatDevice::try_from(x) {
            Ok(device) => {
                let id = device.id.clone();

                let device = ds.entry(device.id.clone()).or_insert(device);

                if let Some(p) = parent_id {
                    device.parents.insert(p);
                }

                for c in x.children.iter() {
                    process_tree(c, Some(id.clone()), ds)
                }
            }
            Err(e) => tracing::warn!("discarding VolumeGroup {:?} due to error {}", x, e),
        },
        devices::Device::LogicalVolume(x) => match FlatDevice::try_from(x) {
            Ok(device) => {
                let id = device.id.clone();

                let device = ds
                    .entry(device.id.clone())
                    .and_modify(|d| d.paths.extend(convert_paths(&x.paths).iter()))
                    .or_insert(device);

                if let Some(p) = parent_id {
                    device.parents.insert(p);
                }

                for c in x.children.iter() {
                    process_tree(c, Some(id.clone()), ds)
                }
            }
            Err(e) => tracing::warn!("discarding LogicalVolume {:?} due to error {}", x, e),
        },
        devices::Device::Zpool(x) => match FlatDevice::try_from(x) {
            Ok(device) => {
                let id = device.id.clone();

                let device = ds.entry(device.id.clone()).or_insert(device);

                if let Some(p) = parent_id {
                    device.parents.insert(p);
                }

                for c in x.children.iter() {
                    process_tree(c, Some(id.clone()), ds)
                }
            }
            Err(e) => tracing::warn!("discarding Zpool {:?} due to error {}", x, e),
        },
        devices::Device::Dataset(x) => match FlatDevice::try_from(x) {
            Ok(device) => {
                let device = ds.entry(device.id.clone()).or_insert(device);

                if let Some(p) = parent_id {
                    device.parents.insert(p);
                }
            }
            Err(e) => tracing::warn!("discarding Dataset {:?} due to error {}", x, e),
        },
    }
}

pub trait TryIntoDeviceId {
    fn try_into_id(&self) -> Result<DeviceId, DeviceError>;
}

impl TryIntoDeviceId for &ScsiDevice {
    fn try_into_id(&self) -> Result<DeviceId, DeviceError> {
        self.serial
            .as_ref()
            .map(|x| format!("{}_{}", self.device_type(), x))
            .map(DeviceId)
            .ok_or_else(|| DeviceError::MissingField("id"))
    }
}

impl TryIntoDeviceId for &Mpath {
    fn try_into_id(&self) -> Result<DeviceId, DeviceError> {
        self.serial
            .as_ref()
            .map(|x| format!("{}_{}", self.device_type(), x))
            .map(DeviceId)
            .ok_or_else(|| DeviceError::MissingField("id"))
    }
}

impl TryIntoDeviceId for &Partition {
    fn try_into_id(&self) -> Result<DeviceId, DeviceError> {
        self.serial
            .as_ref()
            .map(|x| format!("{}{}_{}", self.device_type(), self.partition_number, x))
            .map(DeviceId)
            .ok_or_else(|| DeviceError::MissingField("id"))
    }
}

impl TryIntoDeviceId for &VolumeGroup {
    fn try_into_id(&self) -> Result<DeviceId, DeviceError> {
        Ok(DeviceId(format!("{}_{}", self.device_type(), self.uuid)))
    }
}

impl TryIntoDeviceId for &LogicalVolume {
    fn try_into_id(&self) -> Result<DeviceId, DeviceError> {
        Ok(DeviceId(format!("{}_{}", self.device_type(), self.uuid)))
    }
}

impl TryIntoDeviceId for &Zpool {
    fn try_into_id(&self) -> Result<DeviceId, DeviceError> {
        Ok(DeviceId(format!("{}_{}", self.device_type(), self.guid)))
    }
}

impl TryIntoDeviceId for &Dataset {
    fn try_into_id(&self) -> Result<DeviceId, DeviceError> {
        Ok(DeviceId(format!("{}_{}", self.device_type(), self.guid)))
    }
}

pub trait GetDeviceType {
    fn device_type(&self) -> DeviceType;
}

impl GetDeviceType for &ScsiDevice {
    fn device_type(&self) -> DeviceType {
        DeviceType::ScsiDevice
    }
}

impl GetDeviceType for &Partition {
    fn device_type(&self) -> DeviceType {
        DeviceType::Partition
    }
}

impl GetDeviceType for &Mpath {
    fn device_type(&self) -> DeviceType {
        DeviceType::Mpath
    }
}

impl GetDeviceType for &VolumeGroup {
    fn device_type(&self) -> DeviceType {
        DeviceType::VolumeGroup
    }
}

impl GetDeviceType for &LogicalVolume {
    fn device_type(&self) -> DeviceType {
        DeviceType::LogicalVolume
    }
}

impl GetDeviceType for &Zpool {
    fn device_type(&self) -> DeviceType {
        DeviceType::Zpool
    }
}

impl GetDeviceType for &Dataset {
    fn device_type(&self) -> DeviceType {
        DeviceType::Dataset
    }
}

impl TryIntoDeviceId for &devices::Device {
    fn try_into_id(&self) -> Result<DeviceId, DeviceError> {
        match self {
            devices::Device::ScsiDevice(x) => x.try_into_id(),
            devices::Device::Partition(x) => x.try_into_id(),
            devices::Device::Mpath(x) => x.try_into_id(),
            devices::Device::VolumeGroup(x) => x.try_into_id(),
            devices::Device::LogicalVolume(x) => x.try_into_id(),
            devices::Device::Zpool(x) => x.try_into_id(),
            devices::Device::Dataset(x) => x.try_into_id(),
            devices::Device::MdRaid(_) | devices::Device::Root(_) => unreachable!(),
        }
    }
}

#[derive(Debug, serde::Serialize, Eq, PartialEq, Ord, PartialOrd, Clone)]
pub struct DeviceId(pub String);

/// The current type of Devices we support
#[derive(Debug, serde::Serialize)]
pub enum DeviceType {
    ScsiDevice,
    Partition,
    MdRaid,
    Mpath,
    VolumeGroup,
    LogicalVolume,
    Zpool,
    Dataset,
}

impl std::fmt::Display for DeviceType {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match self {
            DeviceType::ScsiDevice => write!(f, "scsi"),
            DeviceType::Partition => write!(f, "partition"),
            DeviceType::MdRaid => write!(f, "mdraid"),
            DeviceType::Mpath => write!(f, "mpath"),
            DeviceType::VolumeGroup => write!(f, "vg"),
            DeviceType::LogicalVolume => write!(f, "lv"),
            DeviceType::Zpool => write!(f, "zpool"),
            DeviceType::Dataset => write!(f, "dataset"),
        }
    }
}

#[derive(Debug)]
pub enum DeviceError {
    MissingField(&'static str),
}

impl std::fmt::Display for DeviceError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match *self {
            DeviceError::MissingField(ref err) => write!(f, "{}", err),
        }
    }
}

impl std::error::Error for DeviceError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match *self {
            DeviceError::MissingField(_) => None,
        }
    }
}
