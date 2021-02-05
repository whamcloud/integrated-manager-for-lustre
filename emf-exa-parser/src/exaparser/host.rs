// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Default, Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Nics {
    is_bonded: Option<bool>,
    ip: Option<String>,
    netaddr: Option<String>,
    netmask: Option<String>,
    device: Option<String>,
    gateway: Option<String>,
}

#[derive(Default, Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct HostDefaultsSettings {
    pub rest_ext_nic: Option<String>,
    pub rest_cert_server: Option<String>,
    pub ipmi_method: Option<String>,
    pub rest_cert_server_key: Option<String>,
    pub serial_port: String,
    pub rest_cert_ca: Option<String>,
    pub rest_cert_crl: Option<String>,
    pub stonith_type: String,
    pub lnets: Vec<String>,
    pub modprobe_cfg: Option<String>,
    pub rest_primary_nic: Option<String>,
    pub nics: HashMap<String, Nics>,
    pub rest_keepalived_nic: Option<String>,
    pub ipmi_delay: Option<i64>,
    pub host_sfa_list: Vec<String>,
    pub base_ip: HashMap<String, Vec<i64>>,
    pub ipmi_power_wait: i64,
    pub bonding_mode: Option<String>,
    pub nic_list: Vec<String>,
    pub serial_speed: String,
    pub rest_int_nic: Option<String>,
    pub ring1: String,
    pub ring0: String,
    pub grub_args: String,
    pub ipmi_monitor: Option<String>,
    pub stonith_user: Option<String>,
    pub stonith_pass: Option<String>,
}

#[derive(Default, Debug, Clone, PartialEq, Serialize, Deserialize)]

pub struct HostsSettings {
    pub sysctl: HashMap<String, String>,
    pub rest_ext_nic: Option<String>,
    pub rest_cert_server: Option<String>,
    pub ipmi_method: Option<String>,
    pub rest_cert_server_key: Option<String>,
    pub serial_port: String,
    pub rest_cert_ca: Option<String>,
    pub rest_cert_crl: Option<String>,
    pub stonith_type: String,
    pub lnets: Vec<String>,
    pub modprobe_cfg: Option<String>,
    pub rest_primary_nic: Option<String>,
    pub nics: Nics,
    pub rest_keepalived_nic: Option<String>,
    pub lnet_nics: Vec<String>,
    pub ipmi_delay: Option<i64>,
    pub mdt_list: HashMap<String, Vec<i64>>,
    pub host_sfa_list: Vec<String>,
    pub oid: Option<String>,
    pub ha_group: Vec<String>,
    pub ost_list: HashMap<String, Vec<i64>>,
    pub stonith_pass: String,
    pub ipmi_power_wait: i64,
    pub bonding_mode: Option<String>,
    pub stonith_secondary_peers: Vec<String>,
    pub mdt_base_device_paths: HashMap<String, String>,
    pub nic_list: Vec<String>,
    pub peers: Vec<String>,
    pub fs_list: Vec<String>,
    pub name: String,
    pub stonith_primary_peers: Vec<String>,
    pub serial_speed: String,
    pub ost_device_paths: HashMap<String, String>,
    pub rest_int_nic: Option<String>,
    pub lnet_members: HashMap<String, Vec<Vec<String>>>,
    pub ring1: String,
    pub ring0: String,
    pub grub_args: String,
    pub ipmi_monitor: Option<String>,
    pub stonith_user: String,
    pub ha_group_idx: i64,
}
