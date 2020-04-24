// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

#[cfg(feature = "postgres-interop")]
pub use crate::models::ChromaCoreAlertstate;
#[cfg(feature = "postgres-interop")]
use crate::{schema::chroma_core_alertstate as a, Executable};
#[cfg(feature = "postgres-interop")]
use diesel::{dsl, pg::expression::array_comparison::Any, prelude::*};

#[cfg(feature = "postgres-interop")]
pub type AnyRecord = Any<diesel::pg::types::sql_types::Array<dsl::AsExpr<String, a::record_type>>>;
#[cfg(feature = "postgres-interop")]
pub type Table = a::table;
#[cfg(feature = "postgres-interop")]
pub type WithRecordType = dsl::Eq<a::record_type, String>;
#[cfg(feature = "postgres-interop")]
pub type WithRecordTypes = dsl::EqAny<a::record_type, Vec<String>>;
#[cfg(feature = "postgres-interop")]
pub type WithAlertId = dsl::Eq<a::alert_item_id, i32>;
#[cfg(feature = "postgres-interop")]
pub type IsActive = dsl::Eq<a::active, bool>;
#[cfg(feature = "postgres-interop")]
pub type ByActiveRecord = dsl::Filter<Table, dsl::And<WithRecordType, IsActive>>;
#[cfg(feature = "postgres-interop")]
pub type ByActiveRecords = dsl::Filter<Table, dsl::And<WithRecordTypes, IsActive>>;
#[cfg(feature = "postgres-interop")]
pub type UpdateStmt = dsl::Update<Table, (a::active, a::end)>;

#[derive(serde::Serialize, serde::Deserialize, PartialEq, Clone, Copy, Debug)]
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
    UpdatesAvailableAlert,
    TargetOfflineAlert,
    TargetFailoverAlert,
    TargetRecoveryAlert,
    StorageResourceOffline,
    StorageResourceAlert,
    StorageResourceLearnEvent,
    PowerControlDeviceUnavailableAlert,
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

#[cfg(feature = "postgres-interop")]
impl ChromaCoreAlertstate {
    pub fn all() -> Table {
        a::table
    }
    pub fn with_record_type(name: AlertRecordType) -> WithRecordType {
        a::record_type.eq(name.to_string())
    }
    pub fn with_record_types(xs: Vec<AlertRecordType>) -> WithRecordTypes {
        let xs: Vec<_> = xs.iter().map(|x| x.to_string()).collect();

        a::record_type.eq_any(xs)
    }
    pub fn with_alert_item_id(id: i32) -> WithAlertId {
        a::alert_item_id.eq(id)
    }
    pub fn is_active() -> IsActive {
        a::active.eq(true)
    }
    pub fn by_active_record(name: AlertRecordType) -> ByActiveRecord {
        Self::all().filter(Self::with_record_type(name).and(Self::is_active()))
    }
    pub fn by_active_records(xs: Vec<AlertRecordType>) -> ByActiveRecords {
        Self::all().filter(Self::with_record_types(xs).and(Self::is_active()))
    }
}

#[cfg(feature = "postgres-interop")]
pub fn lower(xs: Vec<AlertRecordType>, host_id: i32) -> impl Executable {
    let q = ChromaCoreAlertstate::by_active_records(xs)
        .filter(ChromaCoreAlertstate::with_alert_item_id(host_id));

    diesel::update(q).set((
        a::active.eq(Option::<bool>::None),
        a::end.eq(diesel::dsl::now),
    ))
}

#[cfg(feature = "postgres-interop")]
pub fn raise(
    record_type: AlertRecordType,
    msg: impl ToString,
    item_content_type_id: i32,
    item_id: i32,
) -> impl Executable {
    diesel::insert_into(a::table)
        .values((
            a::record_type.eq(record_type.to_string()),
            a::variant.eq("{}"),
            a::alert_item_id.eq(item_id),
            a::alert_type.eq(record_type.to_string()),
            a::begin.eq(diesel::dsl::now),
            a::message.eq(msg.to_string()),
            a::active.eq(true),
            a::dismissed.eq(false),
            a::severity.eq(40),
            a::alert_item_type_id.eq(item_content_type_id),
        ))
        .on_conflict_do_nothing()
}
