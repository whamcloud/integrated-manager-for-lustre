// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use device_types::{state, udev::UdevCommand};

/// Mutably updates the Udev portion of the device map in response to `UdevCommand`s.
pub fn update_udev(uevents: &state::UEvents, cmd: UdevCommand) -> state::UEvents {
    match cmd {
        UdevCommand::Add(x) | UdevCommand::Change(x) => uevents.update(x.devpath.clone(), x),
        UdevCommand::Remove(x) => uevents.without(&x.devpath),
    }
}

#[cfg(test)]
mod tests {
    use super::update_udev;
    use device_types::{udev::UdevCommand, uevent::UEvent};
    use im::{hashmap, ordset, vector};

    #[test]
    fn test_udev_update() {
        let ev = UEvent {
            major: "253".to_string(),
            minor: "20".to_string(),
            seqnum: 3547,
            paths: ordset![
                "/dev/disk/by-id/dm-uuid-part1-mpath-3600140550e41a841db244a992c31e7df".into(),
                "/dev/mapper/mpathd1".into(),
                "/dev/disk/by-uuid/b4550256-cf48-4013-8363-bfee5f52da12".into(),
                "/dev/disk/by-partuuid/d643e32f-b6b9-4863-af8f-8950376e28da".into(),
                "/dev/dm-20".into(),
                "/dev/disk/by-id/dm-name-mpathd1".into()
            ],
            devname: "/dev/dm-20".into(),
            devpath: "/devices/virtual/block/dm-20".into(),
            devtype: "disk".to_string(),
            vendor: None,
            model: None,
            serial: None,
            fs_type: Some("ext4".to_string()),
            fs_usage: Some("filesystem".to_string()),
            fs_uuid: Some("b4550256-cf48-4013-8363-bfee5f52da12".to_string()),
            fs_label: Some("blah".into()),
            part_entry_number: Some(1),
            part_entry_mm: Some("253:13".to_string()),
            size: Some(100_651_008),
            rotational: Some(false),
            scsi80: Some(
                "SLIO-ORG ost12           50e41a84-1db2-44a9-92c3-1e7dfad48fce".to_string(),
            ),
            scsi83: Some("3600140550e41a841db244a992c31e7df".to_string()),
            read_only: Some(false),
            bios_boot: None,
            zfs_reserved: None,
            is_mpath: None,
            dm_slave_mms: vector!["253:13".to_string()],
            dm_vg_size: Some(0),
            md_devs: ordset![],
            dm_multipath_devpath: None,
            dm_name: Some("mpathd1".to_string()),
            dm_lv_name: None,
            lv_uuid: None,
            dm_vg_name: None,
            vg_uuid: None,
            md_uuid: None,
        };

        let mut ev2 = ev.clone();
        ev2.size = Some(100_651_001);

        let uevents = hashmap! {ev.devpath.clone() => ev.clone()};

        let add_cmd = UdevCommand::Add(ev.clone());

        let uevents = update_udev(&uevents, add_cmd);

        assert_eq!(hashmap! {ev.devpath.clone() => ev.clone()}, uevents);

        let change_cmd = UdevCommand::Change(ev2.clone());

        let uevents = update_udev(&uevents, change_cmd);

        assert_eq!(hashmap! {ev.devpath => ev2.clone()}, uevents);

        let remove_cmd = UdevCommand::Remove(ev2);

        let uevents = update_udev(&uevents, remove_cmd);

        assert_eq!(hashmap! {}, uevents);
    }
}
