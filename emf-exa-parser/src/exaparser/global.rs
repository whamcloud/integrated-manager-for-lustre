// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Default, Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct GlobalSettings {
    pub vg_activation_list: Vec<String>,
    pub clients_list: Vec<String>, //TODO
    pub mgs_fs: String,
    pub s2a_list: Vec<String>,
    pub host_list: Vec<String>,
    pub kdump_path: String,
    pub email_domain: Option<String>,
    pub s2a_pass: String,
    pub pingd: bool,
    pub extra_hosts_start: Vec<String>,
    pub extra_hosts_end: Vec<String>,
    pub lnet_mr_fault_sensitive: bool,
    pub cluster_name: Option<String>,
    pub log_dir: String,
    pub hsm_active: bool,
    pub conf_param_tunings: Option<HashMap<String, String>>,
    pub password_policy: String,
    pub email_list: Vec<String>,
    pub shadow_conf: bool,
    pub s2a_user: String,
    pub mdt_backup: String,
    pub mdt_backup_dir: String,
    pub ntp_list: Vec<String>,
    pub fs_list: Vec<String>,
    pub timezone: Option<String>,
    pub sfa_list: Vec<String>,
    pub set_param_tunings: Option<HashMap<String, String>>,
    pub email_relay: Option<String>,
}
