// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use serde::{Deserialize, Serialize};

#[derive(Default, Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct HaSettings {
    pub crypto_hash: String,
    pub rrp_mode: String,
    pub window_size: i64,
    pub max_messages: i64,
    pub lustre_start_timeout: i64,
    pub netmtu: i64,
    #[serde(rename = "type")]
    pub type_field: String,
    pub stonith_timeout: i64,
    pub start_on_boot: bool,
    pub failover_policy: String,
    pub corosync_nics: Vec<String>,
    pub secauth: String,
    pub ha_groups: Vec<Vec<String>>,
    pub dampen_ifspeed: i64,
    pub mcastport: i64,
    pub crypto_cipher: String,
    pub ha_group_count: i64,
    pub no_quorum_policy: String,
    pub zpool_monitor_timeout: i64,
    pub transport: String,
    pub dampen_ping: i64,
}
