// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_wire_types::db::{
    AlertStateRecord, FsRecord, LnetConfigurationRecord, ManagedHostRecord,
    ManagedTargetMountRecord, ManagedTargetRecord, StratagemConfiguration, TableName,
    VolumeNodeRecord, VolumeRecord, ALERT_STATE_TABLE_NAME, LNET_CONFIGURATION_TABLE_NAME,
    MANAGED_FILESYSTEM_TABLE_NAME, MANAGED_HOST_TABLE_NAME, MANAGED_TARGET_MOUNT_TABLE_NAME,
    MANAGED_TARGET_TABLE_NAME, STRATAGEM_CONFIGURATION_TABLE_NAME, VOLUME_NODE_TABLE_NAME,
    VOLUME_TABLE_NAME,
};
use serde::de::Error;
use std::convert::TryFrom;

/// Records from `chroma` database.
#[derive(Debug)]
pub enum DbRecord {
    ManagedFilesystem(FsRecord),
    ManagedTargetMount(ManagedTargetMountRecord),
    ManagedTarget(ManagedTargetRecord),
    ManagedHost(ManagedHostRecord),
    Volume(VolumeRecord),
    VolumeNode(VolumeNodeRecord),
    AlertState(AlertStateRecord),
    StratagemConfiguration(StratagemConfiguration),
    LnetConfiguration(LnetConfigurationRecord),
}

impl TryFrom<(TableName<'_>, serde_json::Value)> for DbRecord {
    type Error = serde_json::Error;

    /// Performs the conversion. It would be simpler to deserialize from an untagged representation,
    /// but need to check the perf characteristics of it.
    fn try_from((table_name, x): (TableName, serde_json::Value)) -> Result<Self, Self::Error> {
        match table_name {
            MANAGED_FILESYSTEM_TABLE_NAME => {
                serde_json::from_value(x).map(DbRecord::ManagedFilesystem)
            }
            VOLUME_TABLE_NAME => serde_json::from_value(x).map(DbRecord::Volume),
            VOLUME_NODE_TABLE_NAME => serde_json::from_value(x).map(DbRecord::VolumeNode),
            MANAGED_TARGET_MOUNT_TABLE_NAME => {
                serde_json::from_value(x).map(DbRecord::ManagedTargetMount)
            }
            MANAGED_TARGET_TABLE_NAME => serde_json::from_value(x).map(DbRecord::ManagedTarget),
            MANAGED_HOST_TABLE_NAME => serde_json::from_value(x).map(DbRecord::ManagedHost),
            ALERT_STATE_TABLE_NAME => serde_json::from_value(x).map(DbRecord::AlertState),
            STRATAGEM_CONFIGURATION_TABLE_NAME => {
                serde_json::from_value(x).map(DbRecord::StratagemConfiguration)
            }
            LNET_CONFIGURATION_TABLE_NAME => {
                serde_json::from_value(x).map(DbRecord::LnetConfiguration)
            }
            x => Err(serde_json::Error::custom(format!(
                "No matching table representation for {}",
                x
            ))),
        }
    }
}
