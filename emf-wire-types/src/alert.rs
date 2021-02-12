// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    db::{self, TableName},
    ComponentType,
};
use chrono::{DateTime, Utc};

#[derive(
    serde::Serialize, serde::Deserialize, Copy, Clone, Debug, PartialOrd, Ord, PartialEq, Eq,
)]
#[cfg_attr(feature = "postgres-interop", derive(sqlx::Type))]
#[cfg_attr(feature = "graphql", derive(juniper::GraphQLEnum))]
#[repr(i32)]
pub enum AlertSeverity {
    DEBUG = 10,
    INFO = 20,
    WARNING = 30,
    ERROR = 40,
    CRITICAL = 50,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
#[cfg_attr(feature = "postgres-interop", derive(sqlx::Type))]
#[cfg_attr(feature = "postgres-interop", sqlx(type_name = "alert_record_type"))]
pub enum AlertRecordType {
    AlertState,
    LearnEvent,
    AlertEvent,
    SyslogEvent,
    ClientConnectEvent,
    CommandRunningAlert,
    CommandSuccessfulAlert,
    CommandCancelledAlert,
    CommandErroredAlert,
    CorosyncUnknownPeersAlert,
    CorosyncToManyPeersAlert,
    CorosyncNoPeersAlert,
    CorosyncStoppedAlert,
    StonithNotEnabledAlert,
    PacemakerStoppedAlert,
    HostContactAlert,
    HostOfflineAlert,
    HostRebootEvent,
    TargetOfflineAlert,
    TargetRecoveryAlert,
    StorageResourceOffline,
    StorageResourceAlert,
    StorageResourceLearnEvent,
    IpmiBmcUnavailableAlert,
    LNetOfflineAlert,
    LNetNidsChangedAlert,
    StratagemUnconfiguredAlert,
    TimeOutOfSyncAlert,
    NoTimeSyncAlert,
    MultipleTimeSyncAlert,
    UnknownTimeSyncAlert,
}

impl ToString for AlertRecordType {
    fn to_string(&self) -> String {
        serde_json::to_string(self).unwrap().replace("\"", "")
    }
}

/// Record from the `alertstate` table
#[derive(Debug, Eq, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct AlertState {
    pub id: i32,
    pub alert_item_type_id: Option<ComponentType>,
    pub alert_item_id: Option<i32>,
    pub alert_type: String,
    pub begin: DateTime<Utc>,
    pub end: Option<DateTime<Utc>>,
    pub active: Option<bool>,
    pub dismissed: bool,
    pub severity: AlertSeverity,
    pub record_type: AlertRecordType,
    pub variant: String,
    pub lustre_pid: Option<i32>,
    pub message: Option<String>,
}

impl AlertState {
    pub fn is_active(&self) -> bool {
        self.active.is_some()
    }
}

impl db::Id for AlertState {
    fn id(&self) -> i32 {
        self.id
    }
}

impl db::Id for &AlertState {
    fn id(&self) -> i32 {
        self.id
    }
}

pub const ALERT_STATE_TABLE_NAME: TableName = TableName("alertstate");
