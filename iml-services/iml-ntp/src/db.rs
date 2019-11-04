// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_postgres::Client;
use iml_wire_types::db::{AlertStateRecord, ManagedHostRecord, Name};

/// This async function will retrieve the managed host id for a given fqdn. A future
/// containing the managed host id is returned.
pub async fn get_managed_host_items(
    fqdn: &str,
    client: &mut Client,
) -> Result<Option<(i32, i32, String)>, iml_postgres::Error> {
    iml_postgres::select(
        client,
        &format!(
            "SELECT id, content_type_id, state FROM {} WHERE fqdn=$1 AND not_deleted=True;",
            ManagedHostRecord::table_name()
        ),
        &[&fqdn],
    )
    .await
    .map(|row| {
        row.map(|r| {
            (
                r.get::<_, i32>("content_type_id"),
                r.get::<_, i32>("id"),
                r.get::<_, String>("state"),
            )
        })
    })
}

pub async fn get_active_alert_for_fqdn(
    fqdn: &str,
    client: &mut Client,
) -> Result<Option<i32>, iml_postgres::Error> {
    iml_postgres::select(
        client,
        &format!(
            r#"SELECT S.id FROM {} AS S INNER JOIN {} AS MH 
ON S.alert_item_id = MH.id WHERE S.record_type='NtpOutOfSyncAlert' AND 
S.active = True AND MH.fqdn=$1 AND MH.not_deleted = True;"#,
            AlertStateRecord::table_name(),
            ManagedHostRecord::table_name(),
        ),
        &[&fqdn],
    )
    .await
    .map(|row| row.map(|r| r.get::<_, i32>(0)))
}

pub async fn set_alert_inactive(id: i32, client: &mut Client) -> Result<u64, iml_postgres::Error> {
    iml_postgres::update(
        client,
        &format!(
            r#"UPDATE {} SET active=Null, "end"=Now() WHERE id=$1;"#,
            AlertStateRecord::table_name()
        ),
        &[&id],
    )
    .await
}

/// This async function will insert a new entry into the chroma_core_alertstate table. This will effectively raise an
/// NtpOutOfSyncAlert alert for a given fqdn.
pub async fn add_alert(
    fqdn: &str,
    alert_item_type_id: i32,
    alert_item_id: i32,
    client: &mut Client,
) -> Result<u64, iml_postgres::Error> {
    iml_postgres::update(
        client,
        &format!(r#"INSERT INTO {}
                (record_type, variant, alert_item_id, alert_type, begin, message, active, dismissed, severity, alert_item_type_id) values
                ($1, $2, $3, $4, Now(), $5, $6, $7, $8, $9);"#,
                AlertStateRecord::table_name()
            ),
        &[&"NtpOutOfSyncAlert", &"{}", &alert_item_id, &"NtpOutOfSyncAlert", &format!("Ntp is out of sync on server {}", fqdn), &true, &false, &40, &alert_item_type_id]
    ).await
}
