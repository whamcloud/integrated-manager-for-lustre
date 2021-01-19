// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::DevicePath;
use im::{OrdSet, Vector};
use std::path::PathBuf;

#[derive(Debug, PartialEq, serde::Serialize, serde::Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct UEvent {
    pub major: String,
    pub minor: String,
    pub seqnum: i64,
    pub paths: OrdSet<DevicePath>,
    pub devname: PathBuf,
    pub devpath: PathBuf,
    pub devtype: String,
    pub vendor: Option<String>,
    pub model: Option<String>,
    pub serial: Option<String>,
    pub fs_type: Option<String>,
    pub fs_usage: Option<String>,
    pub fs_uuid: Option<String>,
    pub fs_label: Option<String>,
    pub part_entry_number: Option<u64>,
    pub part_entry_mm: Option<String>,
    pub size: Option<u64>,
    pub rotational: Option<bool>,
    pub scsi80: Option<String>,
    pub scsi83: Option<String>,
    pub read_only: Option<bool>,
    pub bios_boot: Option<bool>,
    pub zfs_reserved: Option<bool>,
    pub is_mpath: Option<bool>,
    pub dm_slave_mms: Vector<String>,
    pub dm_vg_size: Option<u64>,
    pub md_devs: OrdSet<DevicePath>,
    pub dm_multipath_devpath: Option<bool>,
    pub dm_name: Option<String>,
    pub dm_lv_name: Option<String>,
    pub lv_uuid: Option<String>,
    pub dm_vg_name: Option<String>,
    pub vg_uuid: Option<String>,
    pub md_uuid: Option<String>,
}
