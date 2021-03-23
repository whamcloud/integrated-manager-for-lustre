// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    db::{self, TableName},
    ComponentType, Meta,
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
#[cfg_attr(feature = "graphql", derive(juniper::GraphQLEnum))]
pub enum AlertRecordType {
    #[cfg_attr(feature = "graphql", graphql(name = "AlertState"))]
    AlertState,
    #[cfg_attr(feature = "graphql", graphql(name = "LearnEvent"))]
    LearnEvent,
    #[cfg_attr(feature = "graphql", graphql(name = "AlertEvent"))]
    AlertEvent,
    #[cfg_attr(feature = "graphql", graphql(name = "SyslogEvent"))]
    SyslogEvent,
    #[cfg_attr(feature = "graphql", graphql(name = "ClientConnectEvent"))]
    ClientConnectEvent,
    #[cfg_attr(feature = "graphql", graphql(name = "CommandRunningAlert"))]
    CommandRunningAlert,
    #[cfg_attr(feature = "graphql", graphql(name = "CommandSuccessfulAlert"))]
    CommandSuccessfulAlert,
    #[cfg_attr(feature = "graphql", graphql(name = "CommandCancelledAlert"))]
    CommandCancelledAlert,
    #[cfg_attr(feature = "graphql", graphql(name = "CommandErroredAlert"))]
    CommandErroredAlert,
    #[cfg_attr(feature = "graphql", graphql(name = "CorosyncUnknownPeersAlert"))]
    CorosyncUnknownPeersAlert,
    #[cfg_attr(feature = "graphql", graphql(name = "CorosyncToManyPeersAlert"))]
    CorosyncToManyPeersAlert,
    #[cfg_attr(feature = "graphql", graphql(name = "CorosyncNoPeersAlert"))]
    CorosyncNoPeersAlert,
    #[cfg_attr(feature = "graphql", graphql(name = "CorosyncStoppedAlert"))]
    CorosyncStoppedAlert,
    #[cfg_attr(feature = "graphql", graphql(name = "StonithNotEnabledAlert"))]
    StonithNotEnabledAlert,
    #[cfg_attr(feature = "graphql", graphql(name = "PacemakerStoppedAlert"))]
    PacemakerStoppedAlert,
    #[cfg_attr(feature = "graphql", graphql(name = "HostContactAlert"))]
    HostContactAlert,
    #[cfg_attr(feature = "graphql", graphql(name = "HostOfflineAlert"))]
    HostOfflineAlert,
    #[cfg_attr(feature = "graphql", graphql(name = "HostRebootEvent"))]
    HostRebootEvent,
    #[cfg_attr(feature = "graphql", graphql(name = "TargetOfflineAlert"))]
    TargetOfflineAlert,
    #[cfg_attr(feature = "graphql", graphql(name = "TargetRecoveryAlert"))]
    TargetRecoveryAlert,
    #[cfg_attr(feature = "graphql", graphql(name = "StorageResourceOffline"))]
    StorageResourceOffline,
    #[cfg_attr(feature = "graphql", graphql(name = "StorageResourceAlert"))]
    StorageResourceAlert,
    #[cfg_attr(feature = "graphql", graphql(name = "StorageResourceLearnEvent"))]
    StorageResourceLearnEvent,
    #[cfg_attr(feature = "graphql", graphql(name = "IpmiBmcUnavailableAlert"))]
    IpmiBmcUnavailableAlert,
    #[cfg_attr(feature = "graphql", graphql(name = "LNetOfflineAlert"))]
    LNetOfflineAlert,
    #[cfg_attr(feature = "graphql", graphql(name = "LNetNidsChangedAlert"))]
    LNetNidsChangedAlert,
    #[cfg_attr(feature = "graphql", graphql(name = "StratagemUnconfiguredAlert"))]
    StratagemUnconfiguredAlert,
    #[cfg_attr(feature = "graphql", graphql(name = "TimeOutOfSyncAlert"))]
    TimeOutOfSyncAlert,
    #[cfg_attr(feature = "graphql", graphql(name = "NoTimeSyncAlert"))]
    NoTimeSyncAlert,
    #[cfg_attr(feature = "graphql", graphql(name = "MultipleTimeSyncAlert"))]
    MultipleTimeSyncAlert,
    #[cfg_attr(feature = "graphql", graphql(name = "UnknownTimeSyncAlert"))]
    UnknownTimeSyncAlert,
}

impl ToString for AlertRecordType {
    fn to_string(&self) -> String {
        serde_json::to_string(self).unwrap().replace("\"", "")
    }
}

/// Record from the `alertstate` table
#[derive(Debug, Eq, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
#[cfg_attr(feature = "graphql", derive(juniper::GraphQLObject))]
pub struct AlertState {
    pub id: i32,
    pub alert_item_type_id: Option<ComponentType>,
    pub alert_item_id: Option<i32>,
    pub alert_type: String,
    pub begin: DateTime<Utc>,
    pub end: Option<DateTime<Utc>>,
    pub active: bool,
    pub dismissed: bool,
    pub severity: AlertSeverity,
    pub record_type: AlertRecordType,
    pub variant: String,
    pub lustre_pid: Option<i32>,
    pub message: Option<String>,
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

#[derive(serde::Serialize, serde::Deserialize, Clone, Debug)]
#[cfg_attr(feature = "graphql", derive(juniper::GraphQLObject))]
pub struct AlertResponse {
    pub data: Vec<AlertState>,
    pub meta: Meta,
}
