// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{listen::MessageType, DbRecord};
use emf_postgres::{sqlx, PgPool};
use emf_wire_types::{
    db::Id,
    sfa::{
        EnclosureType, HealthState, JobState, JobType, MemberState, SfaController, SfaDiskDrive,
        SfaEnclosure, SfaJob, SfaPowerSupply, SfaStorageSystem, SubTargetType,
    },
    snapshot::{ReserveUnit, SnapshotInterval, SnapshotRecord, SnapshotRetention},
    warp_drive::{Cache, Record, RecordChange, RecordId},
    AlertRecordType, AlertSeverity, AlertState, ComponentType, CorosyncResourceBanRecord,
    CorosyncResourceRecord, Filesystem, FsType, Host, OstPoolOstsRecord, OstPoolRecord,
    StratagemConfiguration, TargetRecord,
};
use futures::{lock::Mutex, TryStreamExt};
use std::{fmt::Debug, sync::Arc};

pub type SharedCache = Arc<Mutex<Cache>>;

pub fn db_record_to_change_record((msg_type, record): (MessageType, DbRecord)) -> RecordChange {
    match record {
        DbRecord::Host(x) => match (msg_type, x) {
            (MessageType::Delete, x) => RecordChange::Delete(RecordId::Host(x.id())),
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                RecordChange::Update(Record::Host(x))
            }
        },
        DbRecord::Filesystem(x) => match (msg_type, x) {
            (MessageType::Delete, x) => RecordChange::Delete(RecordId::Filesystem(x.id())),
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                RecordChange::Update(Record::Filesystem(x))
            }
        },
        DbRecord::Target(x) => match (msg_type, x) {
            (MessageType::Delete, x) => RecordChange::Delete(RecordId::Target(x.id())),
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                RecordChange::Update(Record::Target(x))
            }
        },
        DbRecord::AlertState(x) => match (msg_type, x) {
            (MessageType::Delete, x) => RecordChange::Delete(RecordId::ActiveAlert(x.id())),
            (_, x) if !x.is_active() => RecordChange::Delete(RecordId::ActiveAlert(x.id())),
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                RecordChange::Update(Record::ActiveAlert(x))
            }
        },
        DbRecord::OstPool(x) => match (msg_type, x) {
            (MessageType::Delete, x) => RecordChange::Delete(RecordId::OstPool(x.id())),
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                RecordChange::Update(Record::OstPool(x))
            }
        },
        DbRecord::OstPoolOsts(x) => match (msg_type, x) {
            (MessageType::Delete, x) => RecordChange::Delete(RecordId::OstPoolOsts(x.id())),
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                RecordChange::Update(Record::OstPoolOsts(x))
            }
        },
        DbRecord::StratagemConfiguration(x) => match (msg_type, x) {
            (MessageType::Delete, x) => RecordChange::Delete(RecordId::StratagemConfig(x.id())),
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                RecordChange::Update(Record::StratagemConfig(x))
            }
        },
        DbRecord::SfaDiskDrive(x) => match (msg_type, x) {
            (MessageType::Delete, x) => RecordChange::Delete(RecordId::SfaDiskDrive(x.id())),
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                RecordChange::Update(Record::SfaDiskDrive(x))
            }
        },
        DbRecord::SfaEnclosure(x) => match (msg_type, x) {
            (MessageType::Delete, x) => RecordChange::Delete(RecordId::SfaEnclosure(x.id())),
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                RecordChange::Update(Record::SfaEnclosure(x))
            }
        },
        DbRecord::SfaStorageSystem(x) => match (msg_type, x) {
            (MessageType::Delete, x) => RecordChange::Delete(RecordId::SfaStorageSystem(x.id())),
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                RecordChange::Update(Record::SfaStorageSystem(x))
            }
        },
        DbRecord::SfaJob(x) => match (msg_type, x) {
            (MessageType::Delete, x) => RecordChange::Delete(RecordId::SfaJob(x.id())),
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                RecordChange::Update(Record::SfaJob(x))
            }
        },
        DbRecord::SfaPowerSupply(x) => match (msg_type, x) {
            (MessageType::Delete, x) => RecordChange::Delete(RecordId::SfaPowerSupply(x.id())),
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                RecordChange::Update(Record::SfaPowerSupply(x))
            }
        },
        DbRecord::SfaController(x) => match (msg_type, x) {
            (MessageType::Delete, x) => RecordChange::Delete(RecordId::SfaController(x.id())),
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                RecordChange::Update(Record::SfaController(x))
            }
        },
        DbRecord::Snapshot(x) => match (msg_type, x) {
            (MessageType::Delete, x) => RecordChange::Delete(RecordId::Snapshot(x.id)),
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                RecordChange::Update(Record::Snapshot(x))
            }
        },
        DbRecord::SnapshotInterval(x) => match (msg_type, x) {
            (MessageType::Delete, x) => RecordChange::Delete(RecordId::SnapshotInterval(x.id)),
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                RecordChange::Update(Record::SnapshotInterval(x))
            }
        },
        DbRecord::SnapshotRetention(x) => match (msg_type, x) {
            (MessageType::Delete, x) => RecordChange::Delete(RecordId::SnapshotRetention(x.id)),
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                RecordChange::Update(Record::SnapshotRetention(x))
            }
        },
        DbRecord::Lnet(x) => match (msg_type, x) {
            (MessageType::Delete, x) => RecordChange::Delete(RecordId::Lnet(x.id())),
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                RecordChange::Update(Record::Lnet(x))
            }
        },
        DbRecord::AuthGroup(x) => match (msg_type, x) {
            (MessageType::Delete, x) => RecordChange::Delete(RecordId::Group(x.id())),
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                RecordChange::Update(Record::Group(x))
            }
        },
        DbRecord::AuthUser(x) => match (msg_type, x) {
            (MessageType::Delete, x) => RecordChange::Delete(RecordId::User(x.id())),
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                RecordChange::Update(Record::User(x))
            }
        },
        DbRecord::AuthUserGroup(x) => match (msg_type, x) {
            (MessageType::Delete, x) => RecordChange::Delete(RecordId::UserGroup(x.id())),
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                RecordChange::Update(Record::UserGroup(x))
            }
        },
        DbRecord::CorosyncResource(x) => match (msg_type, x) {
            (MessageType::Delete, x) => RecordChange::Delete(RecordId::CorosyncResource(x.id())),
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                RecordChange::Update(Record::CorosyncResource(x))
            }
        },
        DbRecord::CorosyncResourceBan(x) => match (msg_type, x) {
            (MessageType::Delete, x) => RecordChange::Delete(RecordId::CorosyncResourceBan(x.id())),
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                RecordChange::Update(Record::CorosyncResourceBan(x))
            }
        },
    }
}

/// Given a `Cache`, this fn populates it
/// with data from the DB.
pub async fn populate_from_db(
    shared_api_cache: SharedCache,
    pool: &PgPool,
) -> Result<(), emf_postgres::sqlx::Error> {
    let mut cache = shared_api_cache.lock().await;

    cache.active_alert = sqlx::query_as!(
        AlertState,
        r#"
            SELECT
                id,
                alert_item_type_id as "alert_item_type_id: ComponentType",
                alert_item_id,
                alert_type,
                begin,
                "end",
                active,
                dismissed,
                severity as "severity: AlertSeverity",
                record_type as "record_type: AlertRecordType",
                variant,
                lustre_pid,
                message
            FROM alertstate WHERE active = 't'
        "#
    )
    .fetch(pool)
    .map_ok(|x| (x.id(), x))
    .try_collect()
    .await?;

    cache.host = sqlx::query_as!(Host, "SELECT * FROM host")
        .fetch(pool)
        .map_ok(|x| (x.id(), x))
        .try_collect()
        .await?;

    cache.filesystem = sqlx::query_as!(Filesystem, "SELECT * FROM filesystem")
        .fetch(pool)
        .map_ok(|x| (x.id(), x))
        .try_collect()
        .await?;

    cache.corosync_resource = sqlx::query!(
        r#"SELECT id, name, cluster_id, resource_agent, role, active, orphaned, managed,
            failed, failure_ignored, nodes_running_on, (active_node).id AS active_node_id,
            (active_node).name AS active_node_name, mount_point
        FROM corosync_resource"#
    )
    .fetch_all(pool)
    .await?
    .into_iter()
    .map(|x| {
        (
            x.id,
            CorosyncResourceRecord {
                id: x.id,
                name: x.name,
                cluster_id: x.cluster_id,
                resource_agent: x.resource_agent,
                role: x.role,
                active: x.active,
                orphaned: x.orphaned,
                managed: x.managed,
                failed: x.failed,
                failure_ignored: x.failure_ignored,
                nodes_running_on: x.nodes_running_on,
                active_node_id: x.active_node_id,
                active_node_name: x.active_node_name,
                mount_point: x.mount_point,
            },
        )
    })
    .collect();

    cache.corosync_resource_ban = sqlx::query_as!(
        CorosyncResourceBanRecord,
        "SELECT * FROM corosync_resource_bans"
    )
    .fetch(pool)
    .map_ok(|x| (x.id(), x))
    .try_collect()
    .await?;

    cache.target = sqlx::query_as!(
        TargetRecord,
        r#"
        SELECT
            id,
            state,
            name,
            dev_path,
            active_host_id,
            host_ids,
            filesystems,
            uuid,
            mount_path,
            fs_type as "fs_type: FsType"
        FROM target
        "#
    )
    .fetch(pool)
    .map_ok(|x| (x.id(), x))
    .try_collect()
    .await?;

    cache.ost_pool = sqlx::query_as!(OstPoolRecord, "select * from ostpool")
        .fetch(pool)
        .map_ok(|x| (x.id(), x))
        .try_collect()
        .await?;

    cache.ost_pool_osts = sqlx::query_as!(OstPoolOstsRecord, "select * from ostpool_osts")
        .fetch(pool)
        .map_ok(|x| (x.id(), x))
        .try_collect()
        .await?;

    cache.sfa_disk_drive = sqlx::query_as!(
        SfaDiskDrive,
        r#"SELECT
            id,
            index,
            enclosure_index,
            failed,
            slot_number,
            health_state as "health_state: HealthState",
            health_state_reason,
            member_index,
            member_state as "member_state: MemberState",
            storage_system
        FROM sfadiskdrive
        "#
    )
    .fetch(pool)
    .map_ok(|x| (x.id(), x))
    .try_collect()
    .await?;

    cache.sfa_enclosure = sqlx::query_as!(
        SfaEnclosure,
        r#"SELECT
            id,
            index,
            element_name,
            health_state as "health_state: HealthState",
            health_state_reason,
            child_health_state as "child_health_state: HealthState",
            model,
            position,
            enclosure_type as "enclosure_type: EnclosureType",
            canister_location,
            storage_system
        FROM sfaenclosure
        "#
    )
    .fetch(pool)
    .map_ok(|x| (x.id(), x))
    .try_collect()
    .await?;

    cache.sfa_job = sqlx::query_as!(
        SfaJob,
        r#"SELECT
            id,
            index,
            sub_target_index,
            sub_target_type as "sub_target_type: SubTargetType",
            job_type as "job_type: JobType",
            state as "state: JobState",
            storage_system
        FROM sfajob
        "#
    )
    .fetch(pool)
    .map_ok(|x| (x.id(), x))
    .try_collect()
    .await?;

    cache.sfa_power_supply = sqlx::query_as!(
        SfaPowerSupply,
        r#"SELECT
            id,
            index,
            enclosure_index,
            health_state as "health_state: HealthState",
            health_state_reason,
            position,
            storage_system
        FROM sfapowersupply
        "#
    )
    .fetch(pool)
    .map_ok(|x| (x.id(), x))
    .try_collect()
    .await?;

    cache.sfa_storage_system = sqlx::query_as!(
        SfaStorageSystem,
        r#"SELECT
            id,
            uuid,
            platform,
            health_state_reason,
            health_state as "health_state: HealthState",
            child_health_state as "child_health_state: HealthState"
        FROM sfastoragesystem
        "#
    )
    .fetch(pool)
    .map_ok(|x| (x.id(), x))
    .try_collect()
    .await?;

    cache.sfa_controller = sqlx::query_as!(
        SfaController,
        r#"SELECT
            id,
            index,
            enclosure_index,
            health_state as "health_state: HealthState",
            health_state_reason,
            child_health_state as "child_health_state: HealthState",
            storage_system
        FROM sfacontroller
        "#
    )
    .fetch(pool)
    .map_ok(|x| (x.id(), x))
    .try_collect()
    .await?;

    cache.snapshot = sqlx::query_as!(SnapshotRecord, "select * from snapshot")
        .fetch(pool)
        .map_ok(|x| (x.id(), x))
        .try_collect()
        .await?;

    cache.snapshot_interval = sqlx::query!("SELECT * FROM snapshot_interval")
        .fetch(pool)
        .map_ok(|x| {
            (
                x.id,
                SnapshotInterval {
                    id: x.id,
                    filesystem_name: x.filesystem_name,
                    use_barrier: x.use_barrier,
                    interval: x.interval.into(),
                    last_run: x.last_run,
                },
            )
        })
        .try_collect()
        .await?;

    cache.snapshot_retention = sqlx::query_as!(
        SnapshotRetention,
        r#"
        SELECT
            id,
            filesystem_name,
            reserve_value,
            reserve_unit as "reserve_unit:ReserveUnit",
            last_run,
            keep_num
        FROM snapshot_retention
    "#
    )
    .fetch(pool)
    .map_ok(|x| (x.id, x))
    .try_collect()
    .await?;

    cache.stratagem_config = sqlx::query_as!(
        StratagemConfiguration,
        "select * from stratagemconfiguration"
    )
    .fetch(pool)
    .map_ok(|x| (x.id(), x))
    .try_collect()
    .await?;

    tracing::debug!("Populated from db");

    Ok(())
}
