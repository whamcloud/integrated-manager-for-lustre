// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Default, Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct FsSettings {
    pub backfs: String,
    pub mgs_failback: bool,
    pub host_list: Vec<String>,
    pub ost_mke2fs_opts: Option<Vec<String>>,
    pub total_mdt_count: i64,
    pub tune_ost_mke2fs_opts: Option<Vec<String>>,
    pub mdt_base_device_path: Option<String>,
    pub ost_mount_opts: Option<String>,
    pub mdt_opts: String,
    pub mmp_update_interval: i64,
    pub mgs_size: String,
    pub mdt_parts: Option<i64>,
    pub default_ost_count: i64,
    pub default_mdt_count: i64,
    pub mgs_standalone: bool,
    pub dom_max_file_size: i64,
    pub mds_list: Vec<String>,
    pub log_dir: String,
    pub mdt_list: HashMap<String, Vec<i64>>,
    pub hsm_active: bool,
    pub dom_enabled: bool,
    pub mgt_mount_opts: String,
    pub mdt_failback: bool,
    pub mgs_list: Vec<String>,
    pub oss_list: Vec<String>,
    pub ost_opts: Option<String>,
    pub cur_ost_index: i64,
    pub ost_list: HashMap<String, Vec<i64>>,
    pub ost_lnet_list: HashMap<String, Vec<i64>>,
    pub total_ost_count: i64,
    pub name: String,
    pub ost_device_path: Option<String>,
    pub mgs_internal: bool,
    pub mdt_size: String,
    pub cur_mdt_index: i64,
    pub mgs_device_path: Option<String>,
    pub pools: Vec<String>,
    pub mdt_mount_opts: Option<String>,
    pub mdt_mke2fs_opts: Option<Vec<String>>,
}

#[derive(Default, Debug, Clone, PartialEq, Serialize, Deserialize)]

pub struct PoolSettings {
    pub ost_list: Vec<String>,
    pub name: String,
}
