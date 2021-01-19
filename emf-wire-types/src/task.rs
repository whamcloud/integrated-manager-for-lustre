// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use chrono::{DateTime, Utc};
use std::{collections::HashMap, convert::TryFrom};

#[derive(Debug, serde::Serialize)]
#[cfg_attr(feature = "graphql", derive(juniper::GraphQLInputObject))]
pub struct KeyValue {
    pub key: String,
    pub value: String,
}

trait ToHashMap<K, V> {
    fn to_hashmap(self) -> HashMap<K, V>;
}

impl ToHashMap<String, String> for Vec<KeyValue> {
    fn to_hashmap(self) -> HashMap<String, String> {
        self.into_iter().map(|x| (x.key, x.value)).collect()
    }
}

#[cfg_attr(feature = "graphql", derive(juniper::GraphQLObject))]
pub struct KeyValueOut {
    pub key: String,
    pub value: String,
}

trait ToKeyValueOut {
    fn to_key_value(self) -> Vec<KeyValueOut>;
}

impl ToHashMap<String, String> for Vec<KeyValueOut> {
    fn to_hashmap(self) -> HashMap<String, String> {
        self.into_iter().map(|x| (x.key, x.value)).collect()
    }
}

impl ToKeyValueOut for HashMap<String, String> {
    fn to_key_value(self) -> Vec<KeyValueOut> {
        self.into_iter()
            .map(|(key, value)| KeyValueOut { key, value })
            .collect()
    }
}

#[derive(Debug, serde::Serialize)]
#[cfg_attr(feature = "graphql", derive(juniper::GraphQLInputObject))]
pub struct TaskArgs {
    pub name: String,
    #[serde(rename(serialize = "singleRunner"))]
    pub single_runner: bool,
    #[serde(rename(serialize = "keepFailed"))]
    pub keep_failed: bool,
    pub pairs: Vec<KeyValue>,
    pub actions: Vec<String>,
    #[serde(rename(serialize = "needsCleanup"))]
    pub needs_cleanup: bool,
}

#[cfg_attr(feature = "graphql", derive(juniper::GraphQLObject))]
pub struct TaskOut {
    pub id: i32,
    pub name: String,
    pub start: DateTime<Utc>,
    pub finish: Option<DateTime<Utc>>,
    pub state: String,
    pub fids_total: f64,
    pub fids_completed: f64,
    pub fids_failed: f64,
    pub data_transfered: f64,
    pub single_runner: bool,
    pub keep_failed: bool,
    pub actions: Vec<String>,
    pub args: Vec<KeyValueOut>,
    pub filesystem_id: i32,
    pub running_on_id: Option<i32>,
}

#[derive(serde::Serialize, serde::Deserialize, Debug)]
pub struct Task {
    pub id: i32,
    pub name: String,
    pub start: DateTime<Utc>,
    pub finish: Option<DateTime<Utc>>,
    pub state: String,
    pub fids_total: i64,
    pub fids_completed: i64,
    pub fids_failed: i64,
    pub data_transfered: i64,
    pub single_runner: bool,
    pub keep_failed: bool,
    pub actions: Vec<String>,
    pub args: serde_json::Value,
    pub filesystem_id: i32,
    pub running_on_id: Option<i32>,
}

impl TryFrom<Task> for TaskOut {
    type Error = serde_json::Error;

    fn try_from(
        Task {
            id,
            name,
            start,
            finish,
            state,
            fids_total,
            fids_completed,
            fids_failed,
            data_transfered,
            single_runner,
            keep_failed,
            actions,
            args,
            filesystem_id,
            running_on_id,
        }: Task,
    ) -> Result<Self, Self::Error> {
        let args = serde_json::from_value::<HashMap<String, String>>(args)?.to_key_value();

        Ok(Self {
            id,
            name,
            start,
            finish,
            state,
            fids_total: fids_total as f64,
            fids_completed: fids_completed as f64,
            fids_failed: fids_failed as f64,
            data_transfered: data_transfered as f64,
            single_runner,
            keep_failed,
            actions,
            args,
            filesystem_id,
            running_on_id,
        })
    }
}
