// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use serde::{Deserialize, Serialize};

use crate::exaparser::{
    emf::EMFSettings,
    fs::{FsSettings, PoolSettings},
    global::GlobalSettings,
    ha::HaSettings,
    host::{HostDefaultsSettings, HostsSettings},
    sfa::SfaSettings,
};
use std::collections::HashMap;

#[derive(Default, Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ExascalerConfiguration {
    pub ha_settings: HaSettings,
    pub global_settings: GlobalSettings,
    pub pool_settings: HashMap<String, PoolSettings>,
    pub sfa_settings: HashMap<String, SfaSettings>,
    pub zpool_settings: Option<HashMap<String, ZpoolSettings>>,
    pub host_defaults_settings: HostDefaultsSettings,
    pub hosts_settings: HashMap<String, HostsSettings>,
    pub rest_settings: Option<RestSettings>,
    #[serde(rename = "esui_settings")]
    pub emf_settings: EMFSettings,
    pub fs_settings: HashMap<String, FsSettings>,
}

#[derive(Default, Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RestSettings {
    pub ext_vip: String,
    pub ext_vip_fqdn: String,
    pub int_vip: String,
    pub ext_mask: String,
    pub auth_ou: String,
    pub master_nodes: Vec<String>,
    pub ka_vr_id: String,
    pub int_mask: String,
}

#[derive(Default, Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ZpoolSettings {
    pub name: String,
    pub vdevs: Vec<String>,
    pub opts: String,
    pub vdev_base_path: String,
}
