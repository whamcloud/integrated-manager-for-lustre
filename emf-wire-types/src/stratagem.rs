// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    db::{self, TableName},
    Label,
};
use chrono::{DateTime, Utc};

/// The device that is scanned for matching rules.
#[derive(Debug, Eq, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct StratagemDevice {
    pub path: String,
    pub groups: Vec<String>,
}

/// A list of rules + a name for the group of rules.
#[derive(Debug, Eq, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
#[cfg_attr(feature = "graphql", derive(juniper::GraphQLInputObject))]
pub struct StratagemGroup {
    pub rules: Vec<StratagemRule>,
    pub name: String,
}

impl StratagemGroup {
    pub fn get_rule_by_idx(&self, idx: usize) -> Option<&StratagemRule> {
        self.rules.get(idx)
    }
}

/// A rule to match over.
#[derive(Debug, Eq, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
#[cfg_attr(feature = "graphql", derive(juniper::GraphQLInputObject))]
pub struct StratagemRule {
    pub action: String,
    pub expression: String,
    pub argument: String,
    pub counter_name: Option<String>,
}

/// The top-level config
#[derive(Debug, Eq, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct StratagemConfig {
    pub flist_type: String,
    pub summarize_size: bool,
    pub groups: Vec<StratagemGroup>,
    pub device: StratagemDevice,
}

impl StratagemConfig {
    pub fn get_group_by_name(&self, name: &str) -> Option<&StratagemGroup> {
        self.groups.iter().find(|g| g.name == name)
    }
}

#[derive(serde::Serialize, serde::Deserialize, Clone, Debug)]
#[cfg_attr(feature = "graphql", derive(juniper::GraphQLObject))]
/// Information about a stratagem report
pub struct StratagemReport {
    /// The filename of the stratagem report
    pub filename: String,
    /// When the report was last modified
    pub modify_time: DateTime<Utc>,
    /// The size of the report in bytes
    pub size: i32,
}

/// Record from the `chroma_core_stratagemconfiguration` table
#[derive(serde::Serialize, serde::Deserialize, PartialEq, Clone, Debug)]
pub struct StratagemConfiguration {
    pub id: i32,
    pub filesystem_id: i32,
    pub interval: i64,
    pub report_duration: Option<i64>,
    pub purge_duration: Option<i64>,
    pub state: String,
    pub state_modified_at: DateTime<Utc>,
}

impl db::Id for StratagemConfiguration {
    fn id(&self) -> i32 {
        self.id
    }
}

pub const STRATAGEM_CONFIGURATION_TABLE_NAME: TableName = TableName("stratagemconfiguration");

impl Label for StratagemConfiguration {
    fn label(&self) -> &str {
        "Stratagem Configuration"
    }
}

#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
#[cfg_attr(feature = "graphql", derive(juniper::GraphQLObject))]
pub struct StratagemConfigurationOutput {
    pub id: i32,
    pub filesystem_id: i32,
    pub interval: f64,
    pub report_duration: Option<f64>,
    pub purge_duration: Option<f64>,
    pub state: String,
    pub state_modified_at: DateTime<Utc>,
}

impl From<StratagemConfiguration> for StratagemConfigurationOutput {
    fn from(x: StratagemConfiguration) -> Self {
        Self {
            id: x.id,
            filesystem_id: x.filesystem_id,
            interval: x.interval as f64,
            report_duration: x.report_duration.map(|x| x as f64),
            purge_duration: x.purge_duration.map(|x| x as f64),
            state: x.state,
            state_modified_at: x.state_modified_at,
        }
    }
}
