// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    db_record::{self, Name},
    listen::MessageType,
    AlertStateRecord, DbRecord, FsRecord, Id, LnetConfigurationRecord, ManagedHostRecord,
    ManagedTargetMountRecord, ManagedTargetRecord, NotDeleted, StratagemConfiguration,
    VolumeNodeRecord, VolumeRecord,
};
use futures::{future, Future, Stream as _};
use iml_manager_client::{get, get_client, Client, ImlManagerClientError};
use iml_postgres::SharedClient;
use iml_wire_types::{
    Alert, ApiList, EndpointName, Filesystem, Host, Target, TargetConfParam, Volume, VolumeNode,
};
use parking_lot::Mutex;
use std::{collections::HashMap, fmt::Debug, sync::Arc};

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
    ) -> Box<Future<Item = T, Error = ImlManagerClientError> + Send>
    where
        T: Debug + serde::de::DeserializeOwned + EndpointName + ApiQuery + Send,
    {
        Box::new(get(
            client,
            &format!("{}/{}/", T::endpoint_name(), self.id()),
            T::query(),
        ))
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

type BoxedFuture = Box<Future<Item = RecordChange, Error = ImlManagerClientError> + Send>;

fn converter<T>(
    client: Client,
    msg_type: MessageType,
    x: impl ToApiRecord + NotDeleted,
    record_fn: fn(T) -> Record,
    record_id_fn: fn(u32) -> RecordId,
) -> BoxedFuture
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
        (MessageType::Delete, _) => {
            Box::new(future::ok(RecordChange::Delete(record_id_fn(x.id()))))
        }
        (_, x) if x.deleted() => Box::new(future::ok(RecordChange::Delete(record_id_fn(x.id())))),
        (MessageType::Insert, x) | (MessageType::Update, x) => {
            let id = x.id();

            Box::new(
                ToApiRecord::to_api_record(x, client).then(move |r| match r {
                    Ok(x) => Ok(x).map(record_fn).map(RecordChange::Update),
                    Err(ImlManagerClientError::Reqwest(ref e))
                        if e.status() == Some(iml_manager_client::StatusCode::NOT_FOUND) =>
                    {
                        Ok(id).map(record_id_fn).map(RecordChange::Delete)
                    }
                    Err(e) => Err(e),
                }),
            )
        }
    }
}

impl ToApiRecord for ManagedHostRecord {}
impl ToApiRecord for FsRecord {}
impl ToApiRecord for ManagedTargetRecord {}
impl ToApiRecord for VolumeRecord {}
impl ToApiRecord for VolumeNodeRecord {}
impl ToApiRecord for AlertStateRecord {}

pub fn db_record_to_change_record(
    (msg_type, record): (MessageType, DbRecord),
    client: Client,
) -> BoxedFuture {
    match record {
        DbRecord::ManagedHost(x) => converter(client, msg_type, x, Record::Host, RecordId::Host),
        DbRecord::ManagedFilesystem(x) => converter(
            client,
            msg_type,
            x,
            Record::Filesystem,
            RecordId::Filesystem,
        ),
        DbRecord::ManagedTarget(x) => {
            converter(client, msg_type, x, Record::Target, RecordId::Target)
        }
        DbRecord::AlertState(x) => match (msg_type, &x) {
            (MessageType::Delete, x) => Box::new(future::ok(RecordChange::Delete(
                RecordId::ActiveAlert(x.id()),
            ))) as BoxedFuture,
            (_, x) if !x.is_active() => Box::new(future::ok(RecordChange::Delete(
                RecordId::ActiveAlert(x.id()),
            ))) as BoxedFuture,
            (MessageType::Insert, x) | (MessageType::Update, x) => Box::new(
                ToApiRecord::to_api_record(x, client)
                    .map(Record::ActiveAlert)
                    .map(RecordChange::Update),
            ),
        },
        DbRecord::StratagemConfiguration(x) => match (msg_type, x) {
            (MessageType::Delete, x) => Box::new(future::ok(RecordChange::Delete(
                RecordId::StratagemConfig(x.id()),
            ))) as BoxedFuture,
            (_, ref x) if x.deleted() => Box::new(future::ok(RecordChange::Delete(
                RecordId::StratagemConfig(x.id()),
            ))),
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                Box::new(future::ok(RecordChange::Update(Record::StratagemConfig(x))))
            }
        },
        DbRecord::LnetConfiguration(x) => match (msg_type, x) {
            (MessageType::Delete, x) => Box::new(future::ok(RecordChange::Delete(
                RecordId::LnetConfiguration(x.id()),
            ))) as BoxedFuture,
            (_, ref x) if x.deleted() => Box::new(future::ok(RecordChange::Delete(
                RecordId::LnetConfiguration(x.id()),
            ))),
            (MessageType::Insert, x) | (MessageType::Update, x) => Box::new(future::ok(
                RecordChange::Update(Record::LnetConfiguration(x)),
            )),
        },
        DbRecord::ManagedTargetMount(x) => match (msg_type, x) {
            (MessageType::Delete, x) => Box::new(future::ok(RecordChange::Delete(
                RecordId::ManagedTargetMount(x.id()),
            ))) as BoxedFuture,
            (_, ref x) if x.deleted() => Box::new(future::ok(RecordChange::Delete(
                RecordId::ManagedTargetMount(x.id()),
            ))),
            (MessageType::Insert, x) | (MessageType::Update, x) => Box::new(future::ok(
                RecordChange::Update(Record::ManagedTargetMount(x)),
            )),
        },
        DbRecord::Volume(x) => converter(client, msg_type, x, Record::Volume, RecordId::Volume),
        DbRecord::VolumeNode(x) => match (msg_type, x) {
            (MessageType::Delete, x) => Box::new(future::ok(RecordChange::Delete(
                RecordId::VolumeNode(x.id()),
            ))) as BoxedFuture,
            (_, ref x) if x.deleted() => Box::new(future::ok(RecordChange::Delete(
                RecordId::VolumeNode(x.id()),
            ))),
            (MessageType::Insert, x) | (MessageType::Update, x) => {
                Box::new(future::ok(RecordChange::Update(Record::VolumeNode(x))))
            }
        },
    }
}

/// Given a `Cache`, this fn populates it
/// with data from the API.
pub fn populate_from_api(
    shared_api_cache: SharedCache,
) -> impl Future<Item = (), Error = ImlManagerClientError> {
    let client = get_client().unwrap();

    let fs_fut = get(
        client.clone(),
        Filesystem::endpoint_name(),
        Filesystem::query(),
    )
    .map(|fs: ApiList<Filesystem>| fs.objects)
    .map(|fs| fs.into_iter().map(|f| (f.id, f)).collect());

    let target_fut = get(
        client.clone(),
        <Target<TargetConfParam>>::endpoint_name(),
        <Target<TargetConfParam>>::query(),
    )
    .map(|x: ApiList<Target<TargetConfParam>>| x.objects)
    .map(|x| x.into_iter().map(|x| (x.id, x)).collect());

    let active_alert_fut = get(client.clone(), Alert::endpoint_name(), Alert::query())
        .map(|x: ApiList<Alert>| x.objects)
        .map(|x| x.into_iter().map(|x| (x.id, x)).collect());

    let host_fut = get(client.clone(), Host::endpoint_name(), Host::query())
        .map(|x: ApiList<Host>| x.objects)
        .map(|x| x.into_iter().map(|x| (x.id, x)).collect());

    let volume_fut = get(client, Volume::endpoint_name(), Volume::query())
        .map(|x: ApiList<Volume>| x.objects)
        .map(|x| x.into_iter().map(|x| (x.id, x)).collect());

    fs_fut
        .join5(target_fut, active_alert_fut, host_fut, volume_fut)
        .map(move |(filesystem, target, alert, host, volume)| {
            let mut api_cache = shared_api_cache.lock();

            api_cache.filesystem = filesystem;
            api_cache.target = target;
            api_cache.active_alert = alert;
            api_cache.host = host;
            api_cache.volume = volume;
        })
}

fn fetch_from_db<T>(
    client: SharedClient,
    query: &str,
) -> impl Future<Item = HashMap<u32, T>, Error = iml_postgres::Error>
where
    T: From<iml_postgres::Row> + db_record::Name + db_record::Id,
{
    {
        let c = Arc::clone(&client);

        let mut c = c.lock();

        c.prepare(query)
    }
    .map(move |statement| (client, statement))
    .map(|(client, statement)| client.lock().query(&statement, &[]))
    .flatten_stream()
    .fold(HashMap::new(), |mut hm, row| {
        let record = T::from(row);

        hm.insert(record.id(), record);

        Ok(hm)
    })
}

/// Given a `Cache`, this fn populates it
/// with data from the DB.
pub fn populate_from_db(
    shared_api_cache: SharedCache,
    client: SharedClient,
) -> impl Future<Item = (), Error = iml_postgres::Error> {
    let target_mount_fut = fetch_from_db(
        Arc::clone(&client),
        &format!(
            "select * from {} where not_deleted = 't'",
            ManagedTargetMountRecord::table_name()
        ),
    );

    let stratagem_config_fut = fetch_from_db(
        Arc::clone(&client),
        &format!(
            "select * from {} where not_deleted = 't'",
            StratagemConfiguration::table_name()
        ),
    );

    let lnet_config_fut = fetch_from_db(
        Arc::clone(&client),
        &format!(
            "select * from {} where not_deleted = 't'",
            LnetConfigurationRecord::table_name()
        ),
    );

    let volume_node_fut = fetch_from_db(
        Arc::clone(&client),
        &format!(
            "select * from {} where not_deleted = 't'",
            VolumeNodeRecord::table_name()
        ),
    );

    target_mount_fut
        .join4(volume_node_fut, stratagem_config_fut, lnet_config_fut)
        .map(
            move |(
                managed_target_mount,
                volume_node_fut,
                stratagem_configuration,
                lnet_configuration,
            )| {
                let mut cache = shared_api_cache.lock();

                cache.managed_target_mount = managed_target_mount;
                cache.volume_node = volume_node_fut;
                cache.stratagem_config = stratagem_configuration;
                cache.lnet_configuration = lnet_configuration;
            },
        )
}
