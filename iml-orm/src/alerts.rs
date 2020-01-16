// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub use crate::models::ChromaCoreAlertstate;
use crate::{schema::chroma_core_alertstate as a, DbPool};
use diesel::{dsl, pg::expression::array_comparison::Any, prelude::*};
pub use iml_wire_types::AlertRecordType;
use tokio_diesel::AsyncRunQueryDsl;

pub type AnyRecord = Any<diesel::pg::types::sql_types::Array<dsl::AsExpr<String, a::record_type>>>;
pub type Table = a::table;
pub type WithRecordType = dsl::Eq<a::record_type, String>;
pub type WithRecordTypes = dsl::EqAny<a::record_type, Vec<String>>;
pub type WithAlertId = dsl::Eq<a::alert_item_id, i32>;
pub type IsActive = dsl::Eq<a::active, bool>;
pub type ByActiveRecord = dsl::Filter<Table, dsl::And<WithRecordType, IsActive>>;
pub type ByActiveRecords = dsl::Filter<Table, dsl::And<WithRecordTypes, IsActive>>;
pub type UpdateStmt = dsl::Update<Table, (a::active, a::end)>;

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

pub async fn lower(
    xs: Vec<AlertRecordType>,
    host_id: i32,
    pool: &DbPool,
) -> Result<usize, tokio_diesel::AsyncError> {
    let q = ChromaCoreAlertstate::by_active_records(xs)
        .filter(ChromaCoreAlertstate::with_alert_item_id(host_id));

    diesel::update(q)
        .set((
            a::active.eq(Option::<bool>::None),
            a::end.eq(diesel::dsl::now),
        ))
        .execute_async(&pool)
        .await
}

pub async fn lower_one(
    alert: &ChromaCoreAlertstate,
    pool: &DbPool,
) -> Result<usize, tokio_diesel::AsyncError> {
    diesel::update(alert)
        .set((
            a::active.eq(Option::<bool>::None),
            a::end.eq(diesel::dsl::now),
        ))
        .execute_async(&pool)
        .await
}

pub async fn raise(
    record_type: AlertRecordType,
    msg: &str,
    item_content_type_id: i32,
    item_id: i32,
    pool: &DbPool,
) -> Result<usize, tokio_diesel::AsyncError> {
    let rec = record_type.to_string();

    diesel::insert_into(a::table)
        .values((
            a::record_type.eq(&rec),
            a::variant.eq("{}"),
            a::alert_item_id.eq(item_id),
            a::alert_type.eq(&rec),
            a::begin.eq(diesel::dsl::now),
            a::message.eq(msg),
            a::active.eq(true),
            a::dismissed.eq(false),
            a::severity.eq(40),
            a::alert_item_type_id.eq(item_content_type_id),
        ))
        .on_conflict_do_nothing()
        .execute_async(pool)
        .await
}
