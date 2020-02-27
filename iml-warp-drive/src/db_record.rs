// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_wire_types::db::{
    AlertStateRecord, ContentTypeRecord, FsRecord, LnetConfigurationRecord, ManagedHostRecord,
    ManagedTargetMountRecord, ManagedTargetRecord, OstPoolOstsRecord, OstPoolRecord,
    StratagemConfiguration, TableName, VolumeNodeRecord, VolumeRecord, ALERT_STATE_TABLE_NAME,
    CONTENT_TYPE_TABLE_NAME, LNET_CONFIGURATION_TABLE_NAME, MANAGED_FILESYSTEM_TABLE_NAME,
    MANAGED_HOST_TABLE_NAME, MANAGED_TARGET_MOUNT_TABLE_NAME, MANAGED_TARGET_TABLE_NAME,
    OSTPOOL_OSTS_TABLE_NAME, OSTPOOL_TABLE_NAME, STRATAGEM_CONFIGURATION_TABLE_NAME,
    VOLUME_NODE_TABLE_NAME, VOLUME_TABLE_NAME,
};
use serde::de::Error;
use std::convert::TryFrom;

/// Records from `chroma` database.
#[allow(clippy::large_enum_variant)]
#[derive(Debug)]
pub enum DbRecord {
    AlertState(AlertStateRecord),
    ContentType(ContentTypeRecord),
    LnetConfiguration(LnetConfigurationRecord),
    ManagedFilesystem(FsRecord),
    ManagedHost(ManagedHostRecord),
    ManagedTarget(ManagedTargetRecord),
    ManagedTargetMount(ManagedTargetMountRecord),
    OstPool(OstPoolRecord),
    OstPoolOsts(OstPoolOstsRecord),
    StratagemConfiguration(StratagemConfiguration),
    Volume(VolumeRecord),
    VolumeNode(VolumeNodeRecord),
}

impl TryFrom<(TableName<'_>, serde_json::Value)> for DbRecord {
    type Error = serde_json::Error;

    /// Performs the conversion. It would be simpler to deserialize from an untagged representation,
    /// but need to check the perf characteristics of it.
    fn try_from((table_name, x): (TableName, serde_json::Value)) -> Result<Self, Self::Error> {
        match table_name {
            ALERT_STATE_TABLE_NAME => serde_json::from_value(x).map(DbRecord::AlertState),
            CONTENT_TYPE_TABLE_NAME => serde_json::from_value(x).map(DbRecord::ContentType),
            LNET_CONFIGURATION_TABLE_NAME => {
                serde_json::from_value(x).map(DbRecord::LnetConfiguration)
            }
            MANAGED_FILESYSTEM_TABLE_NAME => {
                serde_json::from_value(x).map(DbRecord::ManagedFilesystem)
            }
            MANAGED_HOST_TABLE_NAME => serde_json::from_value(x).map(DbRecord::ManagedHost),
            MANAGED_TARGET_MOUNT_TABLE_NAME => {
                serde_json::from_value(x).map(DbRecord::ManagedTargetMount)
            }
            MANAGED_TARGET_TABLE_NAME => serde_json::from_value(x).map(DbRecord::ManagedTarget),
            OSTPOOL_TABLE_NAME => serde_json::from_value(x).map(DbRecord::OstPool),
            OSTPOOL_OSTS_TABLE_NAME => serde_json::from_value(x).map(DbRecord::OstPoolOsts),
            STRATAGEM_CONFIGURATION_TABLE_NAME => {
                serde_json::from_value(x).map(DbRecord::StratagemConfiguration)
            }
            VOLUME_TABLE_NAME => serde_json::from_value(x).map(DbRecord::Volume),
            VOLUME_NODE_TABLE_NAME => serde_json::from_value(x).map(DbRecord::VolumeNode),
            x => Err(serde_json::Error::custom(format!(
                "No matching table representation for {}",
                x
            ))),
        }
    }
}
