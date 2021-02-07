// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    db::{Id, TableName},
    Label,
};
use std::{
    cmp::Ordering,
    collections::{BTreeMap, BTreeSet},
    fmt,
};

/// An OST Pool record from graphql
#[derive(Debug, Default, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
#[cfg_attr(feature = "graphql", derive(juniper::GraphQLObject))]
pub struct OstPoolGraphql {
    pub id: i32,
    pub name: String,
    pub filesystem: String,
    pub osts: Vec<String>,
}

impl std::fmt::Display for OstPoolGraphql {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(
            f,
            "[#{}] {}.{} [{}]",
            self.id,
            self.filesystem,
            self.name,
            self.osts.join(", ")
        )
    }
}

/// Type Sent between ostpool agent daemon and service
/// FS Name -> Set of OstPools
pub type FsPoolMap = BTreeMap<String, BTreeSet<OstPool>>;

#[derive(Debug, Default, Clone, Eq, serde::Serialize, serde::Deserialize)]
pub struct OstPool {
    pub name: String,
    pub filesystem: String,
    pub osts: Vec<String>,
}

impl std::fmt::Display for OstPool {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(
            f,
            "{}.{} [{}]",
            self.filesystem,
            self.name,
            self.osts.join(", ")
        )
    }
}

impl Ord for OstPool {
    fn cmp(&self, other: &Self) -> Ordering {
        let x = self.filesystem.cmp(&other.filesystem);
        if x != Ordering::Equal {
            return x;
        }
        self.name.cmp(&other.name)
    }
}

impl PartialOrd for OstPool {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl PartialEq for OstPool {
    fn eq(&self, other: &Self) -> bool {
        self.filesystem == other.filesystem && self.name == other.name
    }
}

/// Record from the `chroma_core_ostpool` table
#[derive(serde::Serialize, serde::Deserialize, PartialEq, Clone, Debug)]
pub struct OstPoolRecord {
    pub id: i32,
    pub name: String,
    pub filesystem_id: i32,
}

impl Id for OstPoolRecord {
    fn id(&self) -> i32 {
        self.id
    }
}

impl Id for &OstPoolRecord {
    fn id(&self) -> i32 {
        self.id
    }
}

pub const OSTPOOL_TABLE_NAME: TableName = TableName("ostpool");

impl Label for OstPoolRecord {
    fn label(&self) -> &str {
        &self.name
    }
}

impl Label for &OstPoolRecord {
    fn label(&self) -> &str {
        &self.name
    }
}

/// Record from the `chroma_core_ostpool_osts` table
#[derive(serde::Serialize, serde::Deserialize, PartialEq, Clone, Debug)]
pub struct OstPoolOstsRecord {
    pub id: i32,
    pub ostpool_id: i32,
    pub ost_id: i32,
}

impl Id for OstPoolOstsRecord {
    fn id(&self) -> i32 {
        self.id
    }
}

pub const OSTPOOL_OSTS_TABLE_NAME: TableName = TableName("chroma_core_ostpool_osts");
