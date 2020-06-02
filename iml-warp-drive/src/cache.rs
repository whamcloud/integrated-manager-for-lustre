// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{listen::MessageType, DbRecord};
use futures::{future, lock::Mutex, Future, FutureExt, Stream, TryFutureExt, TryStreamExt};
use im::HashMap;
use iml_manager_client::{get_client, get_retry, Client, ImlManagerClientError};
use iml_postgres::Client as PgClient;
use iml_wire_types::{
    db::{
        AlertStateRecord, AuthGroupRecord, AuthUserGroupRecord, AuthUserRecord, ContentTypeRecord,
        CorosyncConfigurationRecord, FsRecord, Id, LnetConfigurationRecord, ManagedHostRecord,
        ManagedTargetMountRecord, ManagedTargetRecord, Name, NotDeleted, OstPoolOstsRecord,
        OstPoolRecord, PacemakerConfigurationRecord, SfaDiskDrive, SfaEnclosure, SfaJob,
        SfaPowerSupply, SfaStorageSystem, StratagemConfiguration, VolumeNodeRecord, VolumeRecord,
    },
    warp_drive::{Cache, Record, RecordChange, RecordId},
    Alert, ApiList, EndpointName, Filesystem, FlatQuery, Host, Target, TargetConfParam,
};
use std::{fmt::Debug, iter, pin::Pin, sync::Arc};

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
        DbRecord::ManagedTarget(x) => {
            converter(client, msg_type, x, Record::Target, RecordId::Target).await
        }
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

    let target_fut = get_retry(
        client.clone(),
        <Target<TargetConfParam>>::endpoint_name(),
        <Target<TargetConfParam>>::query(),
    )
    .map_ok(|x: ApiList<Target<TargetConfParam>>| x.objects)
    .map_ok(|x: Vec<Target<TargetConfParam>>| x.into_iter().map(|x| (x.id, x)).collect());

    let active_alert_fut = get_retry(client.clone(), Alert::endpoint_name(), Alert::query())
        .map_ok(|x: ApiList<Alert>| x.objects)
        .map_ok(|x: Vec<Alert>| x.into_iter().map(|x| (x.id, x)).collect());

    let host_fut = get_retry(client.clone(), Host::endpoint_name(), Host::query())
        .map_ok(|x: ApiList<Host>| x.objects)
        .map_ok(|x: Vec<Host>| x.into_iter().map(|x| (x.id, x)).collect());

    let (filesystem, target, alert, host) =
        future::try_join4(fs_fut, target_fut, active_alert_fut, host_fut).await?;

    let mut api_cache = shared_api_cache.lock().await;

    api_cache.filesystem = filesystem;
    api_cache.target = target;
    api_cache.active_alert = alert;
    api_cache.host = host;

    tracing::debug!("Populated from api");

    Ok(())
}

async fn into_row<T>(
    s: impl Stream<Item = Result<iml_postgres::Row, iml_postgres::Error>>,
) -> Result<HashMap<i32, T>, iml_postgres::Error>
where
    T: From<iml_postgres::Row> + Name + Id + Clone,
{
    s.map_ok(T::from)
        .map_ok(|record| (record.id(), record))
        .try_collect::<HashMap<i32, T>>()
        .await
}

/// Given a `Cache`, this fn populates it
/// with data from the DB.
pub async fn populate_from_db(
    shared_api_cache: SharedCache,
    client: &mut PgClient,
) -> Result<(), iml_postgres::Error> {
    // The following could be more DRY. However, it allows us to avoid locking
    // the client and enables the use of pipelined requests.
    let stmts = future::try_join_all(vec![
        client.prepare(&format!(
            "select * from {} where not_deleted = 't'",
            ManagedTargetMountRecord::table_name()
        )),
        client.prepare(&format!(
            "select * from {} where not_deleted = 't'",
            StratagemConfiguration::table_name()
        )),
        client.prepare(&format!(
            "select * from {} where not_deleted = 't'",
            LnetConfigurationRecord::table_name()
        )),
        client.prepare(&format!(
            "select * from {} where not_deleted = 't'",
            VolumeRecord::table_name(),
        )),
        client.prepare(&format!(
            "select * from {} where not_deleted = 't'",
            VolumeNodeRecord::table_name()
        )),
        client.prepare(&format!(
            "select * from {} where not_deleted = 't'",
            OstPoolRecord::table_name()
        )),
        client.prepare(&format!(
            "select * from {}",
            OstPoolOstsRecord::table_name()
        )),
        client.prepare(&format!(
            "select * from {}",
            ContentTypeRecord::table_name()
        )),
        client.prepare(&format!("select * from {}", AuthGroupRecord::table_name())),
        client.prepare(&format!("select * from {}", AuthUserRecord::table_name())),
        client.prepare(&format!(
            "select * from {}",
            AuthUserGroupRecord::table_name()
        )),
        client.prepare(&format!(
            "select * from {} where not_deleted = 't'",
            CorosyncConfigurationRecord::table_name()
        )),
        client.prepare(&format!(
            "select * from {} where not_deleted = 't'",
            PacemakerConfigurationRecord::table_name()
        )),
        client.prepare(&format!("select * from {}", SfaStorageSystem::table_name())),
        client.prepare(&format!("select * from {}", SfaEnclosure::table_name())),
        client.prepare(&format!("select * from {}", SfaDiskDrive::table_name())),
        client.prepare(&format!("select * from {}", SfaJob::table_name())),
        client.prepare(&format!("select * from {}", SfaPowerSupply::table_name())),
    ])
    .await?;

    tracing::debug!("Built initial db statements");

    let managed_target_mount = into_row(client.query_raw(&stmts[0], iter::empty()).await?).await?;
    let stratagem_configuration =
        into_row(client.query_raw(&stmts[1], iter::empty()).await?).await?;
    let lnet_configuration = into_row(client.query_raw(&stmts[2], iter::empty()).await?).await?;
    let volume = into_row(client.query_raw(&stmts[3], iter::empty()).await?).await?;
    let volume_node = into_row(client.query_raw(&stmts[4], iter::empty()).await?).await?;

    let ost_pool = into_row(client.query_raw(&stmts[5], iter::empty()).await?).await?;
    let ost_pool_osts = into_row(client.query_raw(&stmts[6], iter::empty()).await?).await?;
    let content_types = into_row(client.query_raw(&stmts[7], iter::empty()).await?).await?;
    let groups = into_row(client.query_raw(&stmts[8], iter::empty()).await?).await?;
    let users = into_row(client.query_raw(&stmts[9], iter::empty()).await?).await?;

    let user_groups = into_row(client.query_raw(&stmts[10], iter::empty()).await?).await?;
    let corosync_configuration =
        into_row(client.query_raw(&stmts[11], iter::empty()).await?).await?;
    let pacemaker_configuration =
        into_row(client.query_raw(&stmts[12], iter::empty()).await?).await?;

    let sfa_storage_system = into_row(client.query_raw(&stmts[13], iter::empty()).await?).await?;

    let sfa_enclosure = into_row(client.query_raw(&stmts[14], iter::empty()).await?).await?;

    let sfa_disk_drive = into_row(client.query_raw(&stmts[15], iter::empty()).await?).await?;

    let sfa_job = into_row(client.query_raw(&stmts[16], iter::empty()).await?).await?;

    let sfa_power_supply = into_row(client.query_raw(&stmts[17], iter::empty()).await?).await?;

    let mut cache = shared_api_cache.lock().await;

    cache.managed_target_mount = managed_target_mount;
    cache.stratagem_config = stratagem_configuration;
    cache.lnet_configuration = lnet_configuration;
    cache.volume = volume;
    cache.volume_node = volume_node;
    cache.ost_pool = ost_pool;
    cache.ost_pool_osts = ost_pool_osts;
    cache.content_type = content_types;
    cache.group = groups;
    cache.user = users;
    cache.user_group = user_groups;
    cache.corosync_configuration = corosync_configuration;
    cache.pacemaker_configuration = pacemaker_configuration;
    cache.sfa_storage_system = sfa_storage_system;
    cache.sfa_enclosure = sfa_enclosure;
    cache.sfa_disk_drive = sfa_disk_drive;
    cache.sfa_job = sfa_job;
    cache.sfa_power_supply = sfa_power_supply;

    tracing::debug!("Populated from db");

    Ok(())
}
