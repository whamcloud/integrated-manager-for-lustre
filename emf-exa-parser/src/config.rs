// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Default, Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ExascalerConfiguration {
    pub ha_settings: HaSettings,
    pub global_settings: GlobalSettings,
    pub pool_settings: HashMap<String, PoolSettings>,
    pub sfa_settings: HashMap<String, SfaSettings>,
    pub zpool_settings: Option<HashMap<String, ZpoolSettings>>,
    pub host_defaults_settings: HostDefaultsSettings,
    pub hosts_settings: HashMap<String, HostSettings>,
    pub rest_settings: Option<RestSettings>,
    pub emf_settings: Option<EMFSettings>,
    pub fs_settings: HashMap<String, FsSettings>,
}

impl ExascalerConfiguration {
    /// Return the list of host names in the same group as hostname
    pub fn ha_group_list(&self, host: &str) -> Vec<String> {
        if self.global_settings.clients_list.contains(&host.into()) {
            vec![]
        } else if let Some(settings) = self.hosts_settings.get(host) {
            self.ha_settings.ha_groups[settings.ha_group_idx as usize].clone()
        } else {
            vec![]
        }
    }
}

#[derive(Default, Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct EMFSettings {
    pub ip: String,
    pub cidr: u32,
    pub size: String,
    pub enabled: bool,
    pub nic: Option<String>,
}

#[derive(Default, Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct FsSettings {
    pub backfs: String,
    pub cur_mdt_index: u64,
    pub cur_ost_index: u64,
    pub default_ost_count: u64,
    pub default_mdt_count: u64,
    pub dom_enabled: bool,
    pub dom_max_file_size: usize,
    pub host_list: Vec<String>,
    pub hsm_active: bool,
    pub log_dir: String,
    pub mds_list: Vec<String>,
    pub mdt_base_device_path: Option<String>,
    pub mdt_failback: bool,
    pub mdt_list: HashMap<String, Vec<u32>>,
    pub mdt_mke2fs_opts: Option<Vec<String>>,
    pub mdt_mount_opts: Option<String>,
    pub mgs_device_path: Option<String>,
    pub mgs_list: Vec<String>,
    pub mgt_mount_opts: String,
    pub mdt_opts: Option<String>,
    pub mdt_parts: Option<u32>,
    pub mdt_size: String,
    pub mgs_failback: bool,
    pub mgs_internal: bool,
    pub mgs_size: String,
    pub mgs_standalone: bool,
    pub mmp_update_interval: usize,
    pub name: String,
    pub oss_list: Vec<String>,
    pub ost_device_path: Option<String>,
    pub ost_list: HashMap<String, Vec<u32>>,
    pub ost_lnet_list: HashMap<String, Vec<u32>>,
    pub ost_mke2fs_opts: Option<Vec<String>>,
    pub ost_mount_opts: Option<String>,
    pub ost_opts: Option<String>,
    pub pools: Vec<String>,
    pub total_mdt_count: u32,
    pub total_ost_count: u32,
    pub tune_ost_mke2fs_opts: Option<Vec<String>>,
}

#[derive(Default, Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct GlobalSettings {
    pub clients_list: Vec<String>,
    pub cluster_name: Option<String>,
    pub conf_param_tunings: Option<HashMap<String, String>>,
    pub email_list: Vec<String>,
    pub email_domain: Option<String>,
    pub email_relay: Option<String>,
    pub extra_hosts_start: Vec<String>,
    pub extra_hosts_end: Vec<String>,
    pub fs_list: Vec<String>,
    pub host_list: Vec<String>,
    pub hsm_active: bool,
    pub kdump_path: String,
    pub lnet_mr_fault_sensitive: bool,
    pub log_dir: String,
    pub mdt_backup: String,
    pub mdt_backup_dir: String,
    pub mgs_fs: String,
    pub ntp_list: Vec<String>,
    pub password_policy: String,
    pub pingd: bool,
    pub s2a_list: Vec<String>,
    pub s2a_pass: String,
    pub s2a_user: String,
    pub set_param_tunings: Option<HashMap<String, String>>,
    pub sfa_list: Vec<String>,
    pub shadow_conf: bool,
    pub timezone: Option<String>,
    pub vg_activation_list: Vec<String>,
}

#[derive(Default, Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct HaSettings {
    pub corosync_nics: Vec<String>,
    pub crypto_cipher: String,
    pub crypto_hash: String,
    pub dampen_ifspeed: u64,
    pub dampen_ping: u64,
    pub failover_policy: String,
    pub ha_group_count: u32,
    pub ha_groups: Vec<Vec<String>>,
    pub lustre_start_timeout: u64,
    pub max_messages: u64,
    pub mcastport: u64,
    pub netmtu: u64,
    pub no_quorum_policy: String,
    pub rrp_mode: String,
    pub secauth: String,
    pub stonith_timeout: u64,
    pub start_on_boot: bool,
    pub transport: String,
    #[serde(rename = "type")]
    pub type_field: String,
    pub window_size: u64,
    pub zpool_monitor_timeout: u64,
}

#[derive(Default, Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct HostDefaultsSettings {
    pub base_ip: HashMap<String, Vec<u32>>,
    pub bonding_mode: Option<String>,
    pub grub_args: Option<String>,
    pub host_sfa_list: Vec<String>,
    pub ipmi_delay: Option<u64>,
    pub ipmi_method: Option<String>,
    pub ipmi_monitor: Option<u64>,
    pub ipmi_power_wait: u64,
    pub lnets: Vec<String>,
    pub modprobe_cfg: Option<String>,
    pub rest_cert_ca: Option<String>,
    pub rest_cert_crl: Option<String>,
    pub rest_cert_server: Option<String>,
    pub rest_cert_server_key: Option<String>,
    pub rest_ext_nic: Option<String>,
    pub rest_int_nic: Option<String>,
    pub rest_keepalived_nic: Option<String>,
    pub rest_primary_nic: Option<String>,
    pub nic_list: Vec<String>,
    pub nics: HashMap<String, Nic>,
    pub ring0: String,
    pub ring1: String,
    pub serial_port: String,
    pub serial_speed: String,
    pub stonith_pass: Option<String>,
    pub stonith_user: Option<String>,
    pub stonith_type: String,
}

#[derive(Default, Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct HostSettings {
    pub fs_list: Vec<String>,
    pub bonding_mode: Option<String>,
    pub grub_args: Option<String>,
    pub ha_group: Vec<String>,
    pub ha_group_idx: u32,
    pub host_sfa_list: Vec<String>,
    pub ipmi_delay: Option<u64>,
    pub ipmi_method: Option<String>,
    pub ipmi_monitor: Option<u64>,
    pub ipmi_power_wait: u64,
    pub lnet_members: HashMap<String, Vec<Vec<String>>>,
    pub lnet_nics: Vec<String>,
    pub lnets: Vec<String>,
    pub mdt_base_device_paths: HashMap<String, String>,
    pub mdt_list: HashMap<String, Vec<u32>>,
    pub modprobe_cfg: Option<String>,
    pub name: String,
    pub nic_list: Vec<String>,
    pub nics: HashMap<String, Nic>,
    pub peers: Vec<String>,
    pub oid: Option<String>,
    pub ost_device_paths: HashMap<String, String>,
    pub ost_list: HashMap<String, Vec<u32>>,
    pub rest_cert_ca: Option<String>,
    pub rest_cert_crl: Option<String>,
    pub rest_ext_nic: Option<String>,
    pub rest_int_nic: Option<String>,
    pub rest_cert_server: Option<String>,
    pub rest_cert_server_key: Option<String>,
    pub rest_keepalived_nic: Option<String>,
    pub rest_primary_nic: Option<String>,
    pub ring0: String,
    pub ring1: String,
    pub serial_port: String,
    pub serial_speed: String,
    pub stonith_pass: String,
    pub stonith_primary_peers: Vec<String>,
    pub stonith_secondary_peers: Vec<String>,
    pub stonith_type: String,
    pub stonith_user: String,
    pub sysctl: HashMap<String, String>,
}

#[derive(Default, Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Nic {
    pub cfg: Option<String>,
    pub device: Option<String>,
    pub gateway: Option<String>,
    pub ip: Option<String>,
    pub is_bonded: Option<bool>,
    pub master: Option<String>,
    pub netaddr: Option<String>,
    pub netmask: Option<String>,
    pub slaves: Option<String>,
}

#[derive(Default, Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PoolSettings {
    pub name: String,
    pub ost_list: Vec<String>,
}

#[derive(Default, Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RestSettings {
    pub auth_ou: String,
    pub ext_mask: String,
    pub ext_vip: String,
    pub ext_vip_fqdn: String,
    pub int_mask: String,
    pub int_vip: String,
    pub ka_vr_id: String,
    pub master_nodes: Vec<String>,
}

#[derive(Default, Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SfaSettings {
    pub controllers: Vec<String>,
    pub name: String,
    pub password: String,
    pub user: String,
}

#[derive(Default, Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ZpoolSettings {
    pub name: String,
    pub opts: String,
    pub vdev_base_path: String,
    pub vdevs: Vec<String>,
}
