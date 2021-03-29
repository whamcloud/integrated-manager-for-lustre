// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    db::{self, TableName},
    ComponentType, Label, ToComponentType,
};
use chrono::{DateTime, Utc};
use std::{convert::TryFrom, fmt};

#[cfg_attr(feature = "graphql", derive(juniper::GraphQLEnum))]
#[cfg_attr(feature = "postgres-interop", derive(sqlx::Type))]
#[cfg_attr(feature = "postgres-interop", sqlx(type_name = "fs_type"))]
#[cfg_attr(feature = "postgres-interop", sqlx(rename_all = "lowercase"))]
#[derive(PartialEq, Eq, Clone, Debug, serde::Serialize, serde::Deserialize, Ord, PartialOrd)]
#[serde(rename_all = "lowercase")]
pub enum FsType {
    #[cfg_attr(feature = "graphql", graphql(name = "zfs"))]
    Zfs,
    #[cfg_attr(feature = "graphql", graphql(name = "ldiskfs"))]
    Ldiskfs,
}

impl TryFrom<&str> for FsType {
    type Error = &'static str;

    fn try_from(x: &str) -> Result<Self, Self::Error> {
        match x {
            "ldiskfs" => Ok(Self::Ldiskfs),
            "zfs" => Ok(Self::Zfs),
            _ => Err("Invalid fs type."),
        }
    }
}

impl TryFrom<String> for FsType {
    type Error = &'static str;

    fn try_from(x: String) -> Result<Self, Self::Error> {
        Self::try_from(x.as_str())
    }
}

impl fmt::Display for FsType {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let label = match self {
            Self::Ldiskfs => "ldiskfs",
            Self::Zfs => "zfs",
        };

        write!(f, "{}", label)
    }
}

#[derive(Debug, Eq, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
#[cfg_attr(feature = "graphql", derive(juniper::GraphQLObject))]
pub struct Filesystem {
    pub id: i32,
    pub state_modified_at: DateTime<Utc>,
    pub state: String,
    pub name: String,
    pub mdt_next_index: i32,
    pub ost_next_index: i32,
    pub mgs_id: i32,
    pub mdt_ids: Vec<i32>,
    pub ost_ids: Vec<i32>,
}

impl db::Id for Filesystem {
    fn id(&self) -> i32 {
        self.id
    }
}

impl db::Id for &Filesystem {
    fn id(&self) -> i32 {
        self.id
    }
}

impl Label for Filesystem {
    fn label(&self) -> &str {
        &self.name
    }
}

impl ToComponentType for Filesystem {
    fn component_type(&self) -> ComponentType {
        ComponentType::Filesystem
    }
}

pub const FILESYSTEM_TABLE_NAME: TableName = TableName("filesystem");
