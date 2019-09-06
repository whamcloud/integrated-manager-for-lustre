// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{listen::MessageType, DbRecord};
use futures::{future, lock::Mutex, Future, FutureExt, Stream, TryFutureExt, TryStreamExt};
use iml_manager_client::{get, get_client, Client, ImlManagerClientError};
use iml_postgres::Client as PgClient;
use iml_wire_types::{
    db::{
        AlertStateRecord, FsRecord, Id, LnetConfigurationRecord, ManagedHostRecord,
        ManagedTargetMountRecord, ManagedTargetRecord, Name, NotDeleted, StratagemConfiguration,
        VolumeNodeRecord, VolumeRecord,
    },
    Alert, ApiList, EndpointName, Filesystem, Host, Target, TargetConfParam, Volume, VolumeNode,
};
use std::{collections::HashMap, fmt::Debug, iter, pin::Pin, sync::Arc};

pub type SharedCache = Arc<Mutex<Cache>>;

#[derive(Default, serde::Serialize, Debug, Clone)]
pub struct Cache {
    pub active_alert: HashMap<u32, Alert>,
    pub filesystem: HashMap<u32, Filesystem>,
    pub host: HashMap<u32, Host>,
    pub lnet_configuration: HashMap<u32, LnetConfigurationRecord>,
    pub managed_target_mount: HashMap<u32, ManagedTargetMountRecord>,
    pub stratagem_config: HashMap<u32, StratagemConfiguration>,
    pub target: HashMap<u32, Target<TargetConfParam>>,
    pub volume: HashMap<u32, Volume>,
    pub volume_node: HashMap<u32, VolumeNodeRecord>,
}

impl Cache {
    /// Removes the record from the cache
    pub fn remove_record(&mut self, x: &RecordId) -> bool {
        match x {
            RecordId::ActiveAlert(id) => self.active_alert.remove(&id).is_some(),
            RecordId::Filesystem(id) => self.filesystem.remove(&id).is_some(),
            RecordId::Host(id) => self.host.remove(&id).is_some(),
            RecordId::LnetConfiguration(id) => self.lnet_configuration.remove(&id).is_some(),
            RecordId::ManagedTargetMount(id) => self.managed_target_mount.remove(&id).is_some(),
            RecordId::StratagemConfig(id) => self.stratagem_config.remove(&id).is_some(),
            RecordId::Target(id) => self.target.remove(&id).is_some(),
            RecordId::Volume(id) => self.volume.remove(&id).is_some(),
            RecordId::VolumeNode(id) => self.volume_node.remove(&id).is_some(),
        }
    }
    /// Inserts the record into the cache
    pub fn insert_record(&mut self, x: Record) {
        match x {
            Record::ActiveAlert(x) => {
                self.active_alert.insert(x.id, x);
            }
            Record::Filesystem(x) => {
                self.filesystem.insert(x.id, x);
            }
            Record::Host(x) => {
                self.host.insert(x.id, x);
            }
            Record::LnetConfiguration(x) => {
                self.lnet_configuration.insert(x.id(), x);
            }
            Record::ManagedTargetMount(x) => {
                self.managed_target_mount.insert(x.id(), x);
            }
            Record::StratagemConfig(x) => {
                self.stratagem_config.insert(x.id(), x);
            }
            Record::Target(x) => {
                self.target.insert(x.id, x);
            }
            Record::Volume(x) => {
                self.volume.insert(x.id, x);
            }
            Record::VolumeNode(x) => {
                self.volume_node.insert(x.id(), x);
            }
        }
    }
}

pub trait ToApiRecord: std::fmt::Debug + Id {
    fn to_api_record<T: 'static>(
        &self,
        client: Client,
    ) -> Pin<Box<dyn Future<Output = Result<T, ImlManagerClientError>> + Send>>
    where
        T: Debug + serde::de::DeserializeOwned + EndpointName + ApiQuery + Send,
    {
        let id = self.id();

        get(
            client,
            format!("{}/{}/", T::endpoint_name(), id),
            T::query(),
        )
        .boxed()
    }
}

pub trait ApiQuery {
    fn query() -> Vec<(&'static str, &'static str)> {
        vec![("limit", "0")]
    }
}

impl ApiQuery for Filesystem {
    fn query() -> Vec<(&'static str, &'static str)> {
        vec![("limit", "0"), ("dehydrate__mgt", "false")]
    }
}

impl<T> ApiQuery for Target<T> {
    fn query() -> Vec<(&'static str, &'static str)> {
        vec![("limit", "0"), ("dehydrate__volume", "false")]
    }
}

impl ApiQuery for Alert {
    fn query() -> Vec<(&'static str, &'static str)> {
        vec![("limit", "0"), ("active", "true")]
    }
}

impl ApiQuery for Host {}
impl ApiQuery for Volume {}
impl ApiQuery for VolumeNode {}

#[derive(serde::Serialize, Debug, Clone)]
#[serde(tag = "tag", content = "payload")]
pub enum Record {
    ActiveAlert(Alert),
    Filesystem(Filesystem),
    Host(Host),
    ManagedTargetMount(ManagedTargetMountRecord),
    StratagemConfig(StratagemConfiguration),
    Target(Target<TargetConfParam>),
    Volume(Volume),
    VolumeNode(VolumeNodeRecord),
    LnetConfiguration(LnetConfigurationRecord),
}

#[derive(Debug, serde::Serialize, Clone)]
#[serde(tag = "tag", content = "payload")]
pub enum RecordId {
    ActiveAlert(u32),
    Filesystem(u32),
    Host(u32),
    ManagedTargetMount(u32),
    StratagemConfig(u32),
    Target(u32),
    Volume(u32),
    VolumeNode(u32),
    LnetConfiguration(u32),
}

#[derive(Debug, serde::Serialize, Clone)]
#[serde(tag = "tag", content = "payload")]
pub enum RecordChange {
    Update(Record),
    Delete(RecordId),
}

async fn converter<T>(
    client: Client,
    msg_type: MessageType,
    x: impl ToApiRecord + NotDeleted,
    record_fn: fn(T) -> Record,
    record_id_fn: fn(u32) -> RecordId,
) -> Result<RecordChange, ImlManagerClientError>
where
    T: std::fmt::Debug
        + serde::de::DeserializeOwned
        + 'static
        + Send
        + Sync
        + EndpointName
        + ApiQuery,
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
        DbRecord::StratagemConfiguration(x) => match (msg_type, x) {
            (MessageType::Delete, x) => Ok(RecordChange::Delete(RecordId::StratagemConfig(x.id()))),
            (_, ref x) if x.deleted() => {
                Ok(RecordChange::Delete(RecordId::StratagemConfig(x.id())))
            }
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                Ok(RecordChange::Update(Record::StratagemConfig(x)))
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
        DbRecord::Volume(x) => {
            converter(client, msg_type, x, Record::Volume, RecordId::Volume).await
        }
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

    let fs_fut = get(
        client.clone(),
        Filesystem::endpoint_name(),
        Filesystem::query(),
    )
    .map_ok(|fs: ApiList<Filesystem>| fs.objects)
    .map_ok(|fs| fs.into_iter().map(|f| (f.id, f)).collect());

    let target_fut = get(
        client.clone(),
        <Target<TargetConfParam>>::endpoint_name(),
        <Target<TargetConfParam>>::query(),
    )
    .map_ok(|x: ApiList<Target<TargetConfParam>>| x.objects)
    .map_ok(|x| x.into_iter().map(|x| (x.id, x)).collect());

    let active_alert_fut = get(client.clone(), Alert::endpoint_name(), Alert::query())
        .map_ok(|x: ApiList<Alert>| x.objects)
        .map_ok(|x| x.into_iter().map(|x| (x.id, x)).collect());

    let host_fut = get(client.clone(), Host::endpoint_name(), Host::query())
        .map_ok(|x: ApiList<Host>| x.objects)
        .map_ok(|x| x.into_iter().map(|x| (x.id, x)).collect());

    let volume_fut = get(client, Volume::endpoint_name(), Volume::query())
        .map_ok(|x: ApiList<Volume>| x.objects)
        .map_ok(|x| x.into_iter().map(|x| (x.id, x)).collect());

    let (filesystem, target, alert, host, volume) =
        future::try_join5(fs_fut, target_fut, active_alert_fut, host_fut, volume_fut).await?;

    let mut api_cache = shared_api_cache.lock().await;

    api_cache.filesystem = filesystem;
    api_cache.target = target;
    api_cache.active_alert = alert;
    api_cache.host = host;
    api_cache.volume = volume;

    tracing::debug!("Populated from api");

    Ok(())
}

async fn into_row<T>(
    s: impl Stream<Item = Result<iml_postgres::Row, iml_postgres::Error>>,
) -> Result<HashMap<u32, T>, iml_postgres::Error>
where
    T: From<iml_postgres::Row> + Name + Id,
{
    s.map_ok(T::from)
        .map_ok(|record| (record.id(), record))
        .try_collect::<HashMap<u32, T>>()
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
    let (target_mount_stmt, stratagem_config_stmt, lnet_config_stmt, volume_node_stmt) =
        future::try_join4(
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
                VolumeNodeRecord::table_name()
            )),
        )
        .await?;

    let (managed_target_mount, stratagem_configuration, lnet_configuration, volume_node) =
        future::try_join4(
            into_row(client.query_raw(&target_mount_stmt, iter::empty()).await?),
            into_row(
                client
                    .query_raw(&stratagem_config_stmt, iter::empty())
                    .await?,
            ),
            into_row(client.query_raw(&lnet_config_stmt, iter::empty()).await?),
            into_row(client.query_raw(&volume_node_stmt, iter::empty()).await?),
        )
        .await?;

    let mut cache = shared_api_cache.lock().await;

    cache.managed_target_mount = managed_target_mount;
    cache.stratagem_config = stratagem_configuration;
    cache.lnet_configuration = lnet_configuration;
    cache.volume_node = volume_node;

    tracing::debug!("Populated from db");

    Ok(())
}
