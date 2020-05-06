use device_types::devices::{
    Device, LogicalVolume, MdRaid, Mpath, Partition, Root, ScsiDevice, VolumeGroup, Zpool,
};
use im::OrdSet;
use std::path::PathBuf;

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

pub fn compare_selected_fields(a: &Device, b: &Device) -> bool {
    selected_fields(a) == selected_fields(b)
}

fn selected_fields(d: &Device) -> Device {
    match d {
        Device::Root(d) => Device::Root(Root {
            children: OrdSet::new(),
            ..d.clone()
        }),
        Device::ScsiDevice(d) => Device::ScsiDevice(ScsiDevice {
            children: OrdSet::new(),
            major: String::new(),
            minor: String::new(),
            devpath: PathBuf::new(),
            paths: OrdSet::new(),
            ..d.clone()
        }),
        Device::Partition(d) => Device::Partition(Partition {
            children: OrdSet::new(),
            major: String::new(),
            minor: String::new(),
            devpath: PathBuf::new(),
            paths: OrdSet::new(),
            ..d.clone()
        }),
        Device::MdRaid(d) => Device::MdRaid(MdRaid {
            children: OrdSet::new(),
            major: String::new(),
            minor: String::new(),
            paths: OrdSet::new(),
            ..d.clone()
        }),
        Device::Mpath(d) => Device::Mpath(Mpath {
            children: OrdSet::new(),
            major: String::new(),
            minor: String::new(),
            devpath: PathBuf::new(),
            paths: OrdSet::new(),
            ..d.clone()
        }),
        Device::VolumeGroup(d) => Device::VolumeGroup(VolumeGroup {
            children: OrdSet::new(),
            ..d.clone()
        }),
        Device::LogicalVolume(d) => Device::LogicalVolume(LogicalVolume {
            children: OrdSet::new(),
            major: String::new(),
            minor: String::new(),
            devpath: PathBuf::new(),
            paths: OrdSet::new(),
            ..d.clone()
        }),
        Device::Zpool(d) => Device::Zpool(Zpool {
            children: OrdSet::new(),
            ..d.clone()
        }),
        Device::Dataset(d) => Device::Dataset(d.clone()),
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
