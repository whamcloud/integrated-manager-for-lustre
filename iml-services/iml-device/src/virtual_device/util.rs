use super::Id;
use device_types::devices::Device;
use im::OrdSet;

pub fn children_owned(d: Device) -> OrdSet<Device> {
    match d {
        Device::Root(dd) => dd.children,
        Device::ScsiDevice(dd) => dd.children,
        Device::Partition(dd) => dd.children,
        Device::MdRaid(dd) => dd.children,
        Device::Mpath(dd) => dd.children,
        Device::VolumeGroup(dd) => dd.children,
        Device::LogicalVolume(dd) => dd.children,
        Device::Zpool(dd) => dd.children,
        Device::Dataset(_) => OrdSet::new(),
    }
}

pub fn children_mut(d: &mut Device) -> Option<&mut OrdSet<Device>> {
    match d {
        Device::Root(dd) => Some(&mut dd.children),
        Device::ScsiDevice(dd) => Some(&mut dd.children),
        Device::Partition(dd) => Some(&mut dd.children),
        Device::MdRaid(dd) => Some(&mut dd.children),
        Device::Mpath(dd) => Some(&mut dd.children),
        Device::VolumeGroup(dd) => Some(&mut dd.children),
        Device::LogicalVolume(dd) => Some(&mut dd.children),
        Device::Zpool(dd) => Some(&mut dd.children),
        Device::Dataset(_) => None,
    }
}

pub fn children(d: &Device) -> Option<&OrdSet<Device>> {
    match d {
        Device::Root(dd) => Some(&dd.children),
        Device::ScsiDevice(dd) => Some(&dd.children),
        Device::Partition(dd) => Some(&dd.children),
        Device::MdRaid(dd) => Some(&dd.children),
        Device::Mpath(dd) => Some(&dd.children),
        Device::VolumeGroup(dd) => Some(&dd.children),
        Device::LogicalVolume(dd) => Some(&dd.children),
        Device::Zpool(dd) => Some(&dd.children),
        Device::Dataset(_) => None,
    }
}

// TODO: This won't tell apart devices of different types with same ids
pub(crate) fn check_id(device: &Device, id: &Id) -> bool {
    match device {
        Device::Root(_) => match id {
            _ => false,
        },
        Device::ScsiDevice(da) => match id {
            Id::Serial(serial) => da
                .serial
                .as_ref()
                .map(|s| if s == serial { true } else { false })
                .unwrap_or(false),
            _ => false,
        },
        Device::Partition(da) => match id {
            Id::Serial(serial) => da
                .serial
                .as_ref()
                .map(|s| if s == serial { true } else { false })
                .unwrap_or(false),
            _ => false,
        },
        Device::MdRaid(da) => match id {
            Id::Uuid(uuid) => {
                if &da.uuid == uuid {
                    true
                } else {
                    false
                }
            }
            _ => false,
        },
        Device::Mpath(da) => match id {
            Id::Serial(serial) => da
                .serial
                .as_ref()
                .map(|s| if s == serial { true } else { false })
                .unwrap_or(false),
            _ => false,
        },
        Device::VolumeGroup(da) => match id {
            Id::Uuid(uuid) => {
                if &da.uuid == uuid {
                    true
                } else {
                    false
                }
            }
            _ => false,
        },
        Device::LogicalVolume(da) => match id {
            Id::Uuid(uuid) => {
                if &da.uuid == uuid {
                    true
                } else {
                    false
                }
            }
            _ => false,
        },
        Device::Zpool(da) => match id {
            Id::Guid(guid) => {
                if &da.guid == guid {
                    true
                } else {
                    false
                }
            }
            _ => false,
        },
        Device::Dataset(da) => match id {
            Id::Guid(guid) => {
                if &da.guid == guid {
                    true
                } else {
                    false
                }
            }
            _ => false,
        },
    }
}

pub(crate) fn compare_by_id(a: &Device, b: &Device) -> bool {
    match a {
        Device::Root(_) => match b {
            Device::Root(_) => true,
            _ => false,
        },
        Device::ScsiDevice(da) => match b {
            Device::ScsiDevice(db) => {
                if da.serial == db.serial {
                    true
                } else {
                    false
                }
            }
            _ => false,
        },
        Device::Partition(da) => match b {
            Device::Partition(db) => {
                if da.serial == db.serial {
                    true
                } else {
                    false
                }
            }
            _ => false,
        },
        Device::MdRaid(da) => match b {
            Device::MdRaid(db) => {
                if da.uuid == db.uuid {
                    true
                } else {
                    false
                }
            }
            _ => false,
        },
        Device::Mpath(da) => match b {
            Device::Mpath(db) => {
                if da.serial == db.serial {
                    true
                } else {
                    false
                }
            }
            _ => false,
        },
        Device::VolumeGroup(da) => match b {
            Device::VolumeGroup(db) => {
                if da.uuid == db.uuid {
                    true
                } else {
                    false
                }
            }
            _ => false,
        },
        Device::LogicalVolume(da) => match b {
            Device::LogicalVolume(db) => {
                if da.uuid == db.uuid {
                    true
                } else {
                    false
                }
            }
            _ => false,
        },
        Device::Zpool(da) => match b {
            Device::Zpool(db) => {
                if da.guid == db.guid {
                    true
                } else {
                    false
                }
            }
            _ => false,
        },
        Device::Dataset(da) => match b {
            Device::Dataset(db) => {
                if da.guid == db.guid {
                    true
                } else {
                    false
                }
            }
            _ => false,
        },
    }
}

pub fn is_virtual(d: &Device) -> bool {
    match d {
        Device::Dataset(_)
        | Device::LogicalVolume(_)
        | Device::MdRaid(_)
        | Device::VolumeGroup(_)
        | Device::Zpool(_) => true,
        _ => false,
    }
}

pub fn to_display(d: &Device) -> String {
    match d {
        Device::Root(d) => format!("Root: children: {}", d.children.len()),
        Device::ScsiDevice(ref d) => format!(
            "ScsiDevice: serial: {}, children: {}",
            d.serial.as_ref().unwrap_or(&"None".into()),
            d.children.len()
        ),
        Device::Partition(d) => format!(
            "Partition: serial: {}, children: {}",
            d.serial.as_ref().unwrap_or(&"None".into()),
            d.children.len()
        ),
        Device::MdRaid(d) => format!("MdRaid: uuid: {}, children: {}", d.uuid, d.children.len()),
        Device::Mpath(d) => format!(
            "Mpath: serial: {}, children: {}",
            d.serial.as_ref().unwrap_or(&"None".into()),
            d.children.len(),
        ),
        Device::VolumeGroup(d) => format!(
            "VolumeGroup: name: {}, children: {}",
            d.name,
            d.children.len()
        ),
        Device::LogicalVolume(d) => format!(
            "LogicalVolume: uuid: {}, children: {}",
            d.uuid,
            d.children.len()
        ),
        Device::Zpool(d) => format!("Zpool: guid: {}, children: {}", d.guid, d.children.len()),
        Device::Dataset(d) => format!("Dataset: guid: {}, children: 0", d.guid),
    }
}
