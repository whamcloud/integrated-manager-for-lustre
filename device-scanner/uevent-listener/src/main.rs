// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

#[cfg(test)]
#[macro_use]
extern crate pretty_assertions;

use device_types::{udev::UdevCommand, uevent::UEvent, Command, DevicePath};
use im::{OrdSet, Vector};
use std::{
    convert::Into, env, io::prelude::*, os::unix::net::UnixStream, process::exit, string::ToString,
};

fn required_field(name: &str) -> String {
    env::var(name).unwrap()
}

fn optional_field(name: &str) -> Option<String> {
    env::var(name).ok()
}

fn split_space(x: &str) -> Vector<String> {
    x.split(' ')
        .filter(|x| x.trim() != "")
        .map(ToString::to_string)
        .collect()
}

fn get_paths() -> OrdSet<DevicePath> {
    let devlinks = env::var("DEVLINKS").unwrap_or_else(|_| "".to_string());

    let devname = required_field("DEVNAME");

    let mut xs: OrdSet<DevicePath> = split_space(&devlinks)
        .iter()
        .map(Into::into)
        .map(DevicePath)
        .collect();

    xs.insert(DevicePath(devname.into()));

    xs
}

fn empty_str_to_none(x: String) -> Option<String> {
    match x.as_str() {
        "" => None,
        y => Some(y.to_string()),
    }
}

fn parse_to<T: std::str::FromStr>(x: String) -> Option<T> {
    x.parse::<T>().ok()
}

fn is_one(x: String) -> bool {
    x == "1"
}

fn lvm_uuids(x: String) -> Option<(String, String)> {
    let lvm_pfix = "LVM-";
    let uuid_len = 32;

    if !x.starts_with(lvm_pfix) {
        None
    } else {
        let uuids = x.get(lvm_pfix.len()..)?;

        if uuids.len() != (uuid_len * 2) {
            None
        } else {
            Some((
                uuids.get(0..uuid_len)?.to_string(),
                uuids.get(uuid_len..)?.to_string(),
            ))
        }
    }
}

fn md_devs<I>(iter: I) -> OrdSet<DevicePath>
where
    I: Iterator<Item = (String, String)>,
{
    iter.filter(|(key, _)| key.starts_with("MD_DEVICE_"))
        .filter(|(key, _)| key.ends_with("_DEV"))
        .map(|(_, v)| v.into())
        .map(DevicePath)
        .collect()
}

pub fn build_uevent() -> UEvent {
    let devname = required_field("DEVNAME").into();
    let devpath = required_field("DEVPATH").into();

    UEvent {
        major: required_field("MAJOR"),
        minor: required_field("MINOR"),
        seqnum: parse_to(required_field("SEQNUM")).expect("Expected SEQNUM to parse to i64"),
        paths: get_paths(),
        devname,
        devpath,
        devtype: required_field("DEVTYPE"),
        vendor: optional_field("ID_VENDOR"),
        model: optional_field("ID_MODEL"),
        serial: optional_field("ID_SERIAL"),
        fs_type: optional_field("ID_FS_TYPE").and_then(empty_str_to_none),
        fs_usage: optional_field("ID_FS_USAGE").and_then(empty_str_to_none),
        fs_uuid: optional_field("ID_FS_UUID").and_then(empty_str_to_none),
        fs_label: optional_field("ID_FS_LABEL").and_then(empty_str_to_none),
        part_entry_number: optional_field("ID_PART_ENTRY_NUMBER").and_then(parse_to),
        part_entry_mm: optional_field("ID_PART_ENTRY_DISK").and_then(empty_str_to_none),
        size: optional_field("EMF_SIZE")
            .and_then(empty_str_to_none)
            .and_then(parse_to)
            .map(|x: u64| x * 512),
        rotational: optional_field("EMF_ROTATIONAL").map(is_one),
        scsi80: optional_field("EMF_SCSI_80").map(|x| x.trim().to_string()),
        scsi83: optional_field("EMF_SCSI_83").map(|x| x.trim().to_string()),
        read_only: optional_field("EMF_IS_RO").map(is_one),
        bios_boot: optional_field("EMF_IS_BIOS_BOOT").map(is_one),
        zfs_reserved: optional_field("EMF_IS_ZFS_RESERVED").map(is_one),
        is_mpath: optional_field("EMF_IS_MPATH").map(is_one),
        dm_slave_mms: optional_field("EMF_DM_SLAVE_MMS")
            .map(|x| split_space(&x))
            .unwrap_or_else(Vector::new),
        dm_vg_size: Some(0),
        md_devs: md_devs(env::vars()),
        dm_multipath_devpath: optional_field("DM_MULTIPATH_DEVICE_PATH").map(is_one),
        dm_name: optional_field("DM_NAME"),
        dm_lv_name: optional_field("DM_LV_NAME"),
        vg_uuid: optional_field("DM_UUID")
            .and_then(lvm_uuids)
            .map(|(x, _)| x),
        lv_uuid: optional_field("DM_UUID")
            .and_then(lvm_uuids)
            .map(|(_, y)| y),
        dm_vg_name: optional_field("DM_VG_NAME"),
        md_uuid: optional_field("MD_UUID"),
    }
}

fn send_data(x: String) {
    let mut stream = UnixStream::connect("/var/run/device-scanner.sock").unwrap();

    stream.write_all(x.as_bytes()).unwrap();
}

fn main() {
    let event = build_uevent();

    let result = match required_field("ACTION").as_ref() {
        "add" => UdevCommand::Add(event),
        "change" => UdevCommand::Change(event),
        "remove" => UdevCommand::Remove(event),
        _ => exit(1),
    };

    let x = serde_json::to_string(&Command::UdevCommand(result)).unwrap();

    send_data(x)
}

#[cfg(test)]
mod tests {
    use super::*;
    use im::ordset;

    #[test]
    fn test_lvm_uuids() {
        let input = "LVM-pV8TgNKMJVNrolJgMhVwg4CAeFFAIMC83Ch5TjlWtPw1BCu2ytrGIjlgzeo7oEtu";

        let result = lvm_uuids(input.to_string());

        assert_eq!(
            result,
            Some((
                "pV8TgNKMJVNrolJgMhVwg4CAeFFAIMC8".to_string(),
                "3Ch5TjlWtPw1BCu2ytrGIjlgzeo7oEtu".to_string()
            ))
        )
    }

    #[test]
    fn test_md_devs() {
        let input = vec![
            ("ACTION".to_string(), "ADD".to_string()),
            ("DEVLINKS".to_string(), "/dev/disk/by-id/md-name-lotus-32vm6:0 /dev/disk/by-id/md-uuid-685b40ee:f2bc2028:f056f6d2:e292c910".to_string()),
            ("DEVNAME".to_string(), "/dev/md0".to_string()),
            ("DEVPATH".to_string(), "/devices/virtual/block/md0".to_string()),
            ("DEVTYPE".to_string(), "disk".to_string()),
            ("ID_FS_TYPE".to_string(), "".to_string()),
            ("EMF_IS_RO".to_string(), "0".to_string()),
            ("EMF_SIZE".to_string(), "41910272".to_string()),
            ("MAJOR".to_string(), "9".to_string()),
            ("MD_DEVICES".to_string(), "2".to_string()),
            ("MD_DEVICE_sda_DEV".to_string(), "/dev/sda".to_string()),
            ("MD_DEVICE_sda_ROLE".to_string(), "0".to_string()),
            ("MD_DEVICE_sdd_DEV".to_string(), "/dev/sdd".to_string()),
            ("MD_DEVICE_sdd_ROLE".to_string(), "1".to_string()),
            ("MD_LEVEL".to_string(), "raid0".to_string()),
            ("MD_METADATA".to_string(), "1.2".to_string()),
            ("MD_NAME".to_string(), "lotus-32vm6:0".to_string()),
            ("MD_UUID".to_string(), "685b40ee:f2bc2028:f056f6d2:e292c910".to_string()),
            ("MINOR".to_string(), "0".to_string()),
            ("MPATH_SBIN_PATH".to_string(), "/sbin".to_string()),
            ("SUBSYSTEM".to_string(), "block".to_string()),
            ("TAGS".to_string(), ":systemd:".to_string()),
            ("USEC_INITIALIZED".to_string(), "426309440135".to_string()),
        ];

        let result = md_devs(input.into_iter());

        assert_eq!(result, ordset!["/dev/sda".into(), "/dev/sdd".into()]);
    }
}
