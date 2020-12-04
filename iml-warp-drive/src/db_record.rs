// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_wire_types::{
    db::{
        AlertStateRecord, AuthGroupRecord, AuthUserGroupRecord, AuthUserRecord, ContentTypeRecord,
        CorosyncConfigurationRecord, FsRecord, LnetConfigurationRecord, ManagedHostRecord,
        ManagedTargetRecord, OstPoolOstsRecord, OstPoolRecord, PacemakerConfigurationRecord,
        StratagemConfiguration, TableName, TargetRecord, VolumeNodeRecord, VolumeRecord,
        ALERT_STATE_TABLE_NAME, AUTH_GROUP_TABLE_NAME, AUTH_USER_GROUP_TABLE_NAME,
        AUTH_USER_TABLE_NAME, CONTENT_TYPE_TABLE_NAME, COROSYNC_CONFIGURATION_TABLE_NAME,
        LNET_CONFIGURATION_TABLE_NAME, MANAGED_FILESYSTEM_TABLE_NAME, MANAGED_HOST_TABLE_NAME,
        MANAGED_TARGET_TABLE_NAME, OSTPOOL_OSTS_TABLE_NAME, OSTPOOL_TABLE_NAME,
        PACEMAKER_CONFIGURATION_TABLE_NAME, STRATAGEM_CONFIGURATION_TABLE_NAME, TARGET_TABLE_NAME,
        VOLUME_NODE_TABLE_NAME, VOLUME_TABLE_NAME,
    },
    sfa::{
        SfaController, SfaDiskDrive, SfaEnclosure, SfaJob, SfaPowerSupply, SfaStorageSystem,
        SFA_CONTROLLER_TABLE_NAME, SFA_DISK_DRIVE_TABLE_NAME, SFA_ENCLOSURE_TABLE_NAME,
        SFA_JOB_TABLE_NAME, SFA_POWER_SUPPLY_TABLE_NAME, SFA_STORAGE_SYSTEM_TABLE_NAME,
    },
    snapshot::{
        SnapshotInterval, SnapshotRecord, SnapshotRetention, SNAPSHOT_INTERVAL_TABLE_NAME,
        SNAPSHOT_RETENTION_TABLE_NAME, SNAPSHOT_TABLE_NAME,
    },
};
use serde::de::Error;
use std::convert::TryFrom;

/// Records from `chroma` database.
#[allow(clippy::large_enum_variant)]
#[derive(Debug)]
pub enum DbRecord {
    AuthGroup(AuthGroupRecord),
    AuthUser(AuthUserRecord),
    AuthUserGroup(AuthUserGroupRecord),
    AlertState(AlertStateRecord),
    ContentType(ContentTypeRecord),
    CorosyncConfiguration(CorosyncConfigurationRecord),
    LnetConfiguration(LnetConfigurationRecord),
    ManagedFilesystem(FsRecord),
    ManagedHost(ManagedHostRecord),
    ManagedTarget(ManagedTargetRecord),
    OstPool(OstPoolRecord),
    OstPoolOsts(OstPoolOstsRecord),
    PacemakerConfiguration(PacemakerConfigurationRecord),
    SfaDiskDrive(SfaDiskDrive),
    SfaEnclosure(SfaEnclosure),
    SfaStorageSystem(SfaStorageSystem),
    SfaJob(SfaJob),
    SfaPowerSupply(SfaPowerSupply),
    SfaController(SfaController),
    Snapshot(SnapshotRecord),
    SnapshotInterval(SnapshotInterval),
    SnapshotRetention(SnapshotRetention),
    StratagemConfiguration(StratagemConfiguration),
    TargetRecord(TargetRecord),
    Volume(VolumeRecord),
    VolumeNode(VolumeNodeRecord),
}

impl TryFrom<(TableName<'_>, serde_json::Value)> for DbRecord {
    type Error = serde_json::Error;

    /// Performs the conversion. It would be simpler to deserialize from an untagged representation,
    /// but need to check the perf characteristics of it.
    fn try_from((table_name, x): (TableName, serde_json::Value)) -> Result<Self, Self::Error> {
        tracing::debug!("Incoming NOTIFY on {}: {:?}", table_name, x);

        match table_name {
            MANAGED_FILESYSTEM_TABLE_NAME => {
                serde_json::from_value(x).map(DbRecord::ManagedFilesystem)
            }
            VOLUME_TABLE_NAME => serde_json::from_value(x).map(DbRecord::Volume),
            VOLUME_NODE_TABLE_NAME => serde_json::from_value(x).map(DbRecord::VolumeNode),
            MANAGED_TARGET_TABLE_NAME => serde_json::from_value(x).map(DbRecord::ManagedTarget),
            MANAGED_HOST_TABLE_NAME => serde_json::from_value(x).map(DbRecord::ManagedHost),
            ALERT_STATE_TABLE_NAME => serde_json::from_value(x).map(DbRecord::AlertState),
            OSTPOOL_TABLE_NAME => serde_json::from_value(x).map(DbRecord::OstPool),
            OSTPOOL_OSTS_TABLE_NAME => serde_json::from_value(x).map(DbRecord::OstPoolOsts),
            SFA_DISK_DRIVE_TABLE_NAME => serde_json::from_value(x).map(DbRecord::SfaDiskDrive),
            SFA_ENCLOSURE_TABLE_NAME => serde_json::from_value(x).map(DbRecord::SfaEnclosure),
            SFA_STORAGE_SYSTEM_TABLE_NAME => {
                serde_json::from_value(x).map(DbRecord::SfaStorageSystem)
            }
            SFA_JOB_TABLE_NAME => serde_json::from_value(x).map(DbRecord::SfaJob),
            SFA_POWER_SUPPLY_TABLE_NAME => serde_json::from_value(x).map(DbRecord::SfaPowerSupply),
            SFA_CONTROLLER_TABLE_NAME => serde_json::from_value(x).map(DbRecord::SfaController),
            STRATAGEM_CONFIGURATION_TABLE_NAME => {
                serde_json::from_value(x).map(DbRecord::StratagemConfiguration)
            }
            SNAPSHOT_TABLE_NAME => serde_json::from_value(x).map(DbRecord::Snapshot),
            SNAPSHOT_INTERVAL_TABLE_NAME => {
                serde_json::from_value(x).map(DbRecord::SnapshotInterval)
            }
            SNAPSHOT_RETENTION_TABLE_NAME => {
                serde_json::from_value(x).map(DbRecord::SnapshotRetention)
            }
            TARGET_TABLE_NAME => serde_json::from_value(x).map(DbRecord::TargetRecord),
            LNET_CONFIGURATION_TABLE_NAME => {
                serde_json::from_value(x).map(DbRecord::LnetConfiguration)
            }
            CONTENT_TYPE_TABLE_NAME => serde_json::from_value(x).map(DbRecord::ContentType),
            AUTH_GROUP_TABLE_NAME => serde_json::from_value(x).map(DbRecord::AuthGroup),
            AUTH_USER_GROUP_TABLE_NAME => serde_json::from_value(x).map(DbRecord::AuthUserGroup),
            AUTH_USER_TABLE_NAME => serde_json::from_value(x).map(DbRecord::AuthUser),
            COROSYNC_CONFIGURATION_TABLE_NAME => {
                serde_json::from_value(x).map(DbRecord::CorosyncConfiguration)
            }
            PACEMAKER_CONFIGURATION_TABLE_NAME => {
                serde_json::from_value(x).map(DbRecord::PacemakerConfiguration)
            }
            x => Err(serde_json::Error::custom(format!(
                "No matching table representation for {}",
                x
            ))),
        }
    }
}
