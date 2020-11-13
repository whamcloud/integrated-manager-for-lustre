// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{listen::MessageType, DbRecord};
use futures::{future, lock::Mutex, Future, FutureExt, TryFutureExt, TryStreamExt};
use iml_manager_client::{get_client, get_retry, Client, ImlManagerClientError};
use iml_postgres::{sqlx, PgPool};
use iml_wire_types::{
    db::{
        AlertStateRecord, AuthGroupRecord, AuthUserGroupRecord, AuthUserRecord, ContentTypeRecord,
        CorosyncConfigurationRecord, FsRecord, Id, LnetConfigurationRecord, ManagedHostRecord,
        ManagedTargetMountRecord, ManagedTargetRecord, NotDeleted, OstPoolOstsRecord,
        OstPoolRecord, PacemakerConfigurationRecord, StratagemConfiguration, TargetRecord,
        VolumeNodeRecord, VolumeRecord,
    },
    sfa::{
        EnclosureType, HealthState, JobState, JobType, MemberState, SfaController, SfaDiskDrive,
        SfaEnclosure, SfaJob, SfaPowerSupply, SfaStorageSystem, SubTargetType,
    },
    snapshot::{ReserveUnit, SnapshotInterval, SnapshotRecord, SnapshotRetention},
    warp_drive::{Cache, Record, RecordChange, RecordId},
    Alert, ApiList, EndpointName, Filesystem, FlatQuery, Host,
};
use std::{fmt::Debug, pin::Pin, sync::Arc};

pub type SharedCache = Arc<Mutex<Cache>>;

pub trait ToApiRecord: std::fmt::Debug + Id {
    fn to_api_record<T: 'static>(
        &self,
        client: Client,
    ) -> Pin<Box<dyn Future<Output = Result<T, ImlManagerClientError>> + Send>>
    where
        T: Debug + serde::de::DeserializeOwned + EndpointName + FlatQuery + Send,
    {
        let id = self.id();

        get_retry(
            client,
            format!("{}/{}/", T::endpoint_name(), id),
            T::query(),
        )
        .boxed()
    }
}

async fn converter<T>(
    client: Client,
    msg_type: MessageType,
    x: impl ToApiRecord + NotDeleted,
    record_fn: fn(T) -> Record,
    record_id_fn: fn(i32) -> RecordId,
) -> Result<RecordChange, ImlManagerClientError>
where
    T: std::fmt::Debug
        + serde::de::DeserializeOwned
        + 'static
        + Send
        + Sync
        + EndpointName
        + FlatQuery,
{
    match (msg_type, &x) {
        (MessageType::Delete, _) => Ok(RecordChange::Delete(record_id_fn(x.id()))),
        (_, x) if x.deleted() => Ok(RecordChange::Delete(record_id_fn(x.id()))),
        (MessageType::Insert, x) | (MessageType::Update, x) => {
            let id = x.id();

            let r = ToApiRecord::to_api_record(x, client).await;

            match r {
                Ok(x) => Ok(x).map(record_fn).map(RecordChange::Update),
                Err(ImlManagerClientError::Reqwest(ref e))
                    if e.status() == Some(iml_manager_client::StatusCode::NOT_FOUND) =>
                {
                    Ok(id).map(record_id_fn).map(RecordChange::Delete)
                }
                Err(e) => Err(e),
            }
        }
    }
}

impl ToApiRecord for ManagedHostRecord {}
impl ToApiRecord for FsRecord {}
impl ToApiRecord for ManagedTargetRecord {}
impl ToApiRecord for VolumeRecord {}
impl ToApiRecord for VolumeNodeRecord {}
impl ToApiRecord for AlertStateRecord {}

pub async fn db_record_to_change_record(
    (msg_type, record): (MessageType, DbRecord),
    client: Client,
) -> Result<RecordChange, ImlManagerClientError> {
    match record {
        DbRecord::ManagedHost(x) => {
            converter(client, msg_type, x, Record::Host, RecordId::Host).await
        }
        DbRecord::ManagedFilesystem(x) => {
            converter(
                client,
                msg_type,
                x,
                Record::Filesystem,
                RecordId::Filesystem,
            )
            .await
        }
        DbRecord::ManagedTarget(x) => match (msg_type, x) {
            (MessageType::Delete, x) => Ok(RecordChange::Delete(RecordId::Target(x.id()))),
            (_, x) if x.deleted() => Ok(RecordChange::Delete(RecordId::Target(x.id()))),
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                Ok(RecordChange::Update(Record::Target(x)))
            }
        },
        DbRecord::AlertState(x) => match (msg_type, &x) {
            (MessageType::Delete, x) => Ok(RecordChange::Delete(RecordId::ActiveAlert(x.id()))),
            (_, x) if !x.is_active() => Ok(RecordChange::Delete(RecordId::ActiveAlert(x.id()))),
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                ToApiRecord::to_api_record(x, client)
                    .map_ok(Record::ActiveAlert)
                    .map_ok(RecordChange::Update)
                    .await
            }
        },
        DbRecord::OstPool(x) => match (msg_type, x) {
            (MessageType::Delete, x) => Ok(RecordChange::Delete(RecordId::OstPool(x.id()))),
            (_, ref x) if x.deleted() => Ok(RecordChange::Delete(RecordId::OstPool(x.id()))),
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                Ok(RecordChange::Update(Record::OstPool(x)))
            }
        },
        DbRecord::OstPoolOsts(x) => match (msg_type, x) {
            (MessageType::Delete, x) => Ok(RecordChange::Delete(RecordId::OstPoolOsts(x.id()))),
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                Ok(RecordChange::Update(Record::OstPoolOsts(x)))
            }
        },
        DbRecord::StratagemConfiguration(x) => match (msg_type, x) {
            (MessageType::Delete, x) => Ok(RecordChange::Delete(RecordId::StratagemConfig(x.id()))),
            (_, ref x) if x.deleted() => {
                Ok(RecordChange::Delete(RecordId::StratagemConfig(x.id())))
            }
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                Ok(RecordChange::Update(Record::StratagemConfig(x)))
            }
        },
        DbRecord::SfaDiskDrive(x) => match (msg_type, x) {
            (MessageType::Delete, x) => Ok(RecordChange::Delete(RecordId::SfaDiskDrive(x.id()))),
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                Ok(RecordChange::Update(Record::SfaDiskDrive(x)))
            }
        },
        DbRecord::SfaEnclosure(x) => match (msg_type, x) {
            (MessageType::Delete, x) => Ok(RecordChange::Delete(RecordId::SfaEnclosure(x.id()))),
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                Ok(RecordChange::Update(Record::SfaEnclosure(x)))
            }
        },
        DbRecord::SfaStorageSystem(x) => match (msg_type, x) {
            (MessageType::Delete, x) => {
                Ok(RecordChange::Delete(RecordId::SfaStorageSystem(x.id())))
            }
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                Ok(RecordChange::Update(Record::SfaStorageSystem(x)))
            }
        },
        DbRecord::SfaJob(x) => match (msg_type, x) {
            (MessageType::Delete, x) => Ok(RecordChange::Delete(RecordId::SfaJob(x.id()))),
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                Ok(RecordChange::Update(Record::SfaJob(x)))
            }
        },
        DbRecord::SfaPowerSupply(x) => match (msg_type, x) {
            (MessageType::Delete, x) => Ok(RecordChange::Delete(RecordId::SfaPowerSupply(x.id()))),
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                Ok(RecordChange::Update(Record::SfaPowerSupply(x)))
            }
        },
        DbRecord::SfaController(x) => match (msg_type, x) {
            (MessageType::Delete, x) => Ok(RecordChange::Delete(RecordId::SfaController(x.id()))),
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                Ok(RecordChange::Update(Record::SfaController(x)))
            }
        },
        DbRecord::Snapshot(x) => match (msg_type, x) {
            (MessageType::Delete, x) => Ok(RecordChange::Delete(RecordId::Snapshot(x.id))),
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                Ok(RecordChange::Update(Record::Snapshot(x)))
            }
        },
        DbRecord::SnapshotInterval(x) => match (msg_type, x) {
            (MessageType::Delete, x) => Ok(RecordChange::Delete(RecordId::SnapshotInterval(x.id))),
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                Ok(RecordChange::Update(Record::SnapshotInterval(x)))
            }
        },
        DbRecord::SnapshotRetention(x) => match (msg_type, x) {
            (MessageType::Delete, x) => Ok(RecordChange::Delete(RecordId::SnapshotRetention(x.id))),
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                Ok(RecordChange::Update(Record::SnapshotRetention(x)))
            }
        },
        DbRecord::LnetConfiguration(x) => match (msg_type, x) {
            (MessageType::Delete, x) => {
                Ok(RecordChange::Delete(RecordId::LnetConfiguration(x.id())))
            }
            (_, ref x) if x.deleted() => {
                Ok(RecordChange::Delete(RecordId::LnetConfiguration(x.id())))
            }
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                Ok(RecordChange::Update(Record::LnetConfiguration(x)))
            }
        },
        DbRecord::ContentType(x) => match (msg_type, x) {
            (MessageType::Delete, x) => Ok(RecordChange::Delete(RecordId::ContentType(x.id()))),
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                Ok(RecordChange::Update(Record::ContentType(x)))
            }
        },
        DbRecord::AuthGroup(x) => match (msg_type, x) {
            (MessageType::Delete, x) => Ok(RecordChange::Delete(RecordId::Group(x.id()))),
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                Ok(RecordChange::Update(Record::Group(x)))
            }
        },
        DbRecord::AuthUser(x) => match (msg_type, x) {
            (MessageType::Delete, x) => Ok(RecordChange::Delete(RecordId::User(x.id()))),
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                Ok(RecordChange::Update(Record::User(x)))
            }
        },
        DbRecord::AuthUserGroup(x) => match (msg_type, x) {
            (MessageType::Delete, x) => Ok(RecordChange::Delete(RecordId::UserGroup(x.id()))),
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                Ok(RecordChange::Update(Record::UserGroup(x)))
            }
        },
        DbRecord::CorosyncConfiguration(x) => match (msg_type, x) {
            (MessageType::Delete, x) => Ok(RecordChange::Delete(RecordId::CorosyncConfiguration(
                x.id(),
            ))),
            (_, ref x) if x.deleted() => Ok(RecordChange::Delete(RecordId::CorosyncConfiguration(
                x.id(),
            ))),
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                Ok(RecordChange::Update(Record::CorosyncConfiguration(x)))
            }
        },
        DbRecord::PacemakerConfiguration(x) => match (msg_type, x) {
            (MessageType::Delete, x) => Ok(RecordChange::Delete(RecordId::PacemakerConfiguration(
                x.id(),
            ))),
            (_, ref x) if x.deleted() => Ok(RecordChange::Delete(
                RecordId::PacemakerConfiguration(x.id()),
            )),
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                Ok(RecordChange::Update(Record::PacemakerConfiguration(x)))
            }
        },
        DbRecord::ManagedTargetMount(x) => match (msg_type, x) {
            (MessageType::Delete, x) => {
                Ok(RecordChange::Delete(RecordId::ManagedTargetMount(x.id())))
            }
            (_, ref x) if x.deleted() => {
                Ok(RecordChange::Delete(RecordId::ManagedTargetMount(x.id())))
            }
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                Ok(RecordChange::Update(Record::ManagedTargetMount(x)))
            }
        },
        DbRecord::TargetRecord(x) => match (msg_type, x) {
            (MessageType::Delete, x) => Ok(RecordChange::Delete(RecordId::TargetRecord(x.id()))),
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                Ok(RecordChange::Update(Record::TargetRecord(x)))
            }
        },
        DbRecord::Volume(x) => match (msg_type, x) {
            (MessageType::Delete, x) => Ok(RecordChange::Delete(RecordId::Volume(x.id()))),
            (_, ref x) if x.deleted() => Ok(RecordChange::Delete(RecordId::Volume(x.id()))),
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                Ok(RecordChange::Update(Record::Volume(x)))
            }
        },
        DbRecord::VolumeNode(x) => match (msg_type, x) {
            (MessageType::Delete, x) => Ok(RecordChange::Delete(RecordId::VolumeNode(x.id()))),
            (_, ref x) if x.deleted() => Ok(RecordChange::Delete(RecordId::VolumeNode(x.id()))),
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                Ok(RecordChange::Update(Record::VolumeNode(x)))
            }
        },
    }
}

/// Given a `Cache`, this fn populates it
/// with data from the API.
pub async fn populate_from_api(shared_api_cache: SharedCache) -> Result<(), ImlManagerClientError> {
    let client = get_client().unwrap();

    let fs_fut = get_retry(
        client.clone(),
        Filesystem::endpoint_name(),
        Filesystem::query(),
    )
    .map_ok(|fs: ApiList<Filesystem>| fs.objects)
    .map_ok(|fs: Vec<Filesystem>| fs.into_iter().map(|f| (f.id, f)).collect());

    let active_alert_fut = get_retry(client.clone(), Alert::endpoint_name(), Alert::query())
        .map_ok(|x: ApiList<Alert>| x.objects)
        .map_ok(|x: Vec<Alert>| x.into_iter().map(|x| (x.id, x)).collect());

    let host_fut = get_retry(client.clone(), Host::endpoint_name(), Host::query())
        .map_ok(|x: ApiList<Host>| x.objects)
        .map_ok(|x: Vec<Host>| x.into_iter().map(|x| (x.id, x)).collect());

    let (filesystem, alert, host) = future::try_join3(fs_fut, active_alert_fut, host_fut).await?;

    let mut api_cache = shared_api_cache.lock().await;

    api_cache.filesystem = filesystem;
    api_cache.active_alert = alert;
    api_cache.host = host;

    tracing::debug!("Populated from api");

    Ok(())
}

/// Given a `Cache`, this fn populates it
/// with data from the DB.
pub async fn populate_from_db(
    shared_api_cache: SharedCache,
    pool: &PgPool,
) -> Result<(), iml_postgres::sqlx::Error> {
    let mut cache = shared_api_cache.lock().await;

    cache.content_type = sqlx::query_as!(ContentTypeRecord, "select * from django_content_type")
        .fetch(pool)
        .map_ok(|x| (x.id(), x))
        .try_collect()
        .await?;

    cache.corosync_configuration = sqlx::query_as!(
        CorosyncConfigurationRecord,
        "select * from chroma_core_corosyncconfiguration where not_deleted = 't'"
    )
    .fetch(pool)
    .map_ok(|x| (x.id(), x))
    .try_collect()
    .await?;

    cache.group = sqlx::query_as!(AuthGroupRecord, "select * from auth_group")
        .fetch(pool)
        .map_ok(|x| (x.id(), x))
        .try_collect()
        .await?;

    cache.lnet_configuration = sqlx::query_as!(
        LnetConfigurationRecord,
        "select * from chroma_core_lnetconfiguration where not_deleted = 't'"
    )
    .fetch(pool)
    .map_ok(|x| (x.id(), x))
    .try_collect()
    .await?;

    cache.target = sqlx::query_as!(
        ManagedTargetRecord,
        "select * from chroma_core_managedtarget where not_deleted = 't'"
    )
    .fetch(pool)
    .map_ok(|x| (x.id(), x))
    .try_collect()
    .await?;

    cache.managed_target_mount = sqlx::query_as!(
        ManagedTargetMountRecord,
        "select * from chroma_core_managedtargetmount where not_deleted = 't'"
    )
    .fetch(pool)
    .map_ok(|x| (x.id(), x))
    .try_collect()
    .await?;

    cache.target_record = sqlx::query_as!(TargetRecord, "SELECT * FROM target")
        .fetch(pool)
        .map_ok(|x| (x.id(), x))
        .try_collect()
        .await?;

    cache.ost_pool = sqlx::query_as!(
        OstPoolRecord,
        "select * from chroma_core_ostpool where not_deleted = 't'"
    )
    .fetch(pool)
    .map_ok(|x| (x.id(), x))
    .try_collect()
    .await?;

    cache.ost_pool_osts =
        sqlx::query_as!(OstPoolOstsRecord, "select * from chroma_core_ostpool_osts")
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
        FROM chroma_core_sfadiskdrive
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
        FROM chroma_core_sfaenclosure
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
        FROM chroma_core_sfajob
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
        FROM chroma_core_sfapowersupply
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
        FROM chroma_core_sfastoragesystem
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
        FROM chroma_core_sfacontroller
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
        "select * from chroma_core_stratagemconfiguration where not_deleted = 't'"
    )
    .fetch(pool)
    .map_ok(|x| (x.id(), x))
    .try_collect()
    .await?;

    cache.user = sqlx::query_as!(
        AuthUserRecord,
        r#"
        SELECT
            id,
            is_superuser,
            username,
            first_name,
            last_name,
            email,
            is_staff,
            is_active
        FROM auth_user
    "#
    )
    .fetch(pool)
    .map_ok(|x| (x.id(), x))
    .try_collect()
    .await?;

    cache.user_group = sqlx::query_as!(AuthUserGroupRecord, "select * from auth_user_groups")
        .fetch(pool)
        .map_ok(|x| (x.id(), x))
        .try_collect()
        .await?;

    cache.pacemaker_configuration = sqlx::query_as!(
        PacemakerConfigurationRecord,
        "select * from chroma_core_pacemakerconfiguration where not_deleted = 't'"
    )
    .fetch(pool)
    .map_ok(|x| (x.id(), x))
    .try_collect()
    .await?;

    cache.volume = sqlx::query_as!(
        VolumeRecord,
        "select * from chroma_core_volume where not_deleted = 't'"
    )
    .fetch(pool)
    .map_ok(|x| (x.id(), x))
    .try_collect()
    .await?;

    cache.volume_node = sqlx::query_as!(
        VolumeNodeRecord,
        "select * from chroma_core_volumenode where not_deleted = 't'"
    )
    .fetch(pool)
    .map_ok(|x| (x.id(), x))
    .try_collect()
    .await?;

    tracing::debug!("Populated from db");

    Ok(())
}
