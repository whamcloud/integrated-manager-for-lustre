// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use emf_wire_types::{
    db::{
        AuthGroupRecord, AuthUserGroupRecord, AuthUserRecord, TableName, AUTH_GROUP_TABLE_NAME,
        AUTH_USER_GROUP_TABLE_NAME, AUTH_USER_TABLE_NAME,
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
    AlertState, CorosyncResourceBanRecord, CorosyncResourceRecord, Filesystem, Host, Lnet,
    OstPoolOstsRecord, OstPoolRecord, StratagemConfiguration, TargetRecord, ALERT_STATE_TABLE_NAME,
    COROSYNC_RESOURCE_BAN_TABLE_NAME, COROSYNC_RESOURCE_TABLE_NAME, FILESYSTEM_TABLE_NAME,
    HOST_TABLE_NAME, LNET_TABLE_NAME, OSTPOOL_OSTS_TABLE_NAME, OSTPOOL_TABLE_NAME,
    STRATAGEM_CONFIGURATION_TABLE_NAME, TARGET_TABLE_NAME,
};
use serde::de::Error;
use std::convert::TryFrom;

/// Records from `chroma` database.
#[allow(clippy::large_enum_variant)]
#[derive(Debug)]
pub enum DbRecord {
    AlertState(AlertState),
    AuthGroup(AuthGroupRecord),
    AuthUser(AuthUserRecord),
    AuthUserGroup(AuthUserGroupRecord),
    CorosyncResource(CorosyncResourceRecord),
    CorosyncResourceBan(CorosyncResourceBanRecord),
    Filesystem(Filesystem),
    Host(Host),
    Lnet(Lnet),
    OstPool(OstPoolRecord),
    OstPoolOsts(OstPoolOstsRecord),
    SfaController(SfaController),
    SfaDiskDrive(SfaDiskDrive),
    SfaEnclosure(SfaEnclosure),
    SfaJob(SfaJob),
    SfaPowerSupply(SfaPowerSupply),
    SfaStorageSystem(SfaStorageSystem),
    Snapshot(SnapshotRecord),
    SnapshotInterval(SnapshotInterval),
    SnapshotRetention(SnapshotRetention),
    StratagemConfiguration(StratagemConfiguration),
    Target(TargetRecord),
}

impl TryFrom<(TableName<'_>, serde_json::Value)> for DbRecord {
    type Error = serde_json::Error;

    /// Performs the conversion. It would be simpler to deserialize from an untagged representation,
    /// but need to check the perf characteristics of it.
    fn try_from((table_name, x): (TableName, serde_json::Value)) -> Result<Self, Self::Error> {
        tracing::debug!("Incoming NOTIFY on {}: {:?}", table_name, x);

        match table_name {
            FILESYSTEM_TABLE_NAME => serde_json::from_value(x).map(DbRecord::Filesystem),
            HOST_TABLE_NAME => serde_json::from_value(x).map(DbRecord::Host),
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
            TARGET_TABLE_NAME => serde_json::from_value(x).map(DbRecord::Target),
            LNET_TABLE_NAME => serde_json::from_value(x).map(DbRecord::Lnet),
            AUTH_GROUP_TABLE_NAME => serde_json::from_value(x).map(DbRecord::AuthGroup),
            AUTH_USER_GROUP_TABLE_NAME => serde_json::from_value(x).map(DbRecord::AuthUserGroup),
            AUTH_USER_TABLE_NAME => serde_json::from_value(x).map(DbRecord::AuthUser),
            COROSYNC_RESOURCE_TABLE_NAME => {
                serde_json::from_value(x).map(DbRecord::CorosyncResource)
            }
            COROSYNC_RESOURCE_BAN_TABLE_NAME => {
                serde_json::from_value(x).map(DbRecord::CorosyncResourceBan)
            }
            x => Err(serde_json::Error::custom(format!(
                "No matching table representation for {}",
                x
            ))),
        }
    }
}
