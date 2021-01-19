// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

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
