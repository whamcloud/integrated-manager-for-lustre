// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    db::{AuthGroupRecord, AuthUserGroupRecord, AuthUserRecord, Id},
    sfa::{SfaController, SfaDiskDrive, SfaEnclosure, SfaJob, SfaPowerSupply, SfaStorageSystem},
    snapshot::{SnapshotInterval, SnapshotRecord, SnapshotRetention},
    AlertState, ComponentType, CompositeId, CorosyncResourceBanRecord, CorosyncResourceRecord,
    Filesystem, Host, Label, Lnet, OstPoolOstsRecord, OstPoolRecord, StratagemConfiguration,
    TargetRecord, ToCompositeId,
};
use im::HashMap;
use std::{
    fmt,
    hash::{BuildHasher, Hash},
    iter::FusedIterator,
    ops::Deref,
    sync::Arc,
};

/// This trait is to bring method `arc_values()` to the collections of
/// type HashMap<K, Arc<V>> to simplify iterating through the values.
/// Example:
/// ```rust,no_run
///     use std::sync::Arc;
///     use im::HashMap;
///     use emf_wire_types::warp_drive::ArcValuesExt;
///
///     let hm: HashMap<i32, Arc<String>> = im::hashmap!(
///         1 => Arc::new("one".to_string()),
///         2 => Arc::new("two".to_string()),
///     );
///     let vals: Vec<&str> = hm.arc_values().map(|s| &s[..]).collect();
///     println!("values are: {:?}", vals);
/// ```
pub trait ArcValuesExt<K, V> {
    fn arc_values(&self) -> ArcValues<K, V>;
}

// the newtype around the iterator from the library
pub struct ArcValues<'a, K: 'a, V: 'a>(im::hashmap::Values<'a, K, Arc<V>>);

impl<'a, K, V, S> ArcValuesExt<K, V> for HashMap<K, Arc<V>, S>
where
    K: Hash + Eq + Copy,
    V: Clone,
    S: BuildHasher,
{
    fn arc_values(&self) -> ArcValues<K, V> {
        ArcValues(self.values())
    }
}

impl<'a, K, V> Iterator for ArcValues<'a, K, V> {
    type Item = &'a V;

    fn next(&mut self) -> Option<Self::Item> {
        self.0.next().map(|v| &**v)
    }

    fn size_hint(&self) -> (usize, Option<usize>) {
        self.0.size_hint()
    }
}

impl<'a, K, V> ExactSizeIterator for ArcValues<'a, K, V> {}

impl<'a, K, V> FusedIterator for ArcValues<'a, K, V> {}

fn hashmap_to_arc_hashmap<K, V>(hm: &HashMap<K, V>) -> HashMap<K, Arc<V>>
where
    K: Hash + Eq + Copy,
    V: Clone,
{
    hm.iter().map(|(k, v)| (*k, Arc::new(v.clone()))).collect()
}

fn arc_hashmap_to_hashmap<K, V>(hm: &HashMap<K, Arc<V>>) -> HashMap<K, V>
where
    K: Hash + Eq + Copy,
    V: Clone,
{
    hm.iter().map(|(k, v)| (*k, (**v).clone())).collect()
}

#[derive(serde::Serialize, serde::Deserialize, Default, PartialEq, Clone, Debug)]
pub struct Cache {
    pub corosync_resource: HashMap<i32, CorosyncResourceRecord>,
    pub corosync_resource_ban: HashMap<i32, CorosyncResourceBanRecord>,
    pub active_alert: HashMap<i32, AlertState>,
    pub filesystem: HashMap<i32, Filesystem>,
    pub group: HashMap<i32, AuthGroupRecord>,
    pub host: HashMap<i32, Host>,
    pub lnet: HashMap<i32, Lnet>,
    pub ost_pool: HashMap<i32, OstPoolRecord>,
    pub ost_pool_osts: HashMap<i32, OstPoolOstsRecord>,
    pub sfa_disk_drive: HashMap<i32, SfaDiskDrive>,
    pub sfa_enclosure: HashMap<i32, SfaEnclosure>,
    pub sfa_job: HashMap<i32, SfaJob>,
    pub sfa_power_supply: HashMap<i32, SfaPowerSupply>,
    pub sfa_storage_system: HashMap<i32, SfaStorageSystem>,
    pub sfa_controller: HashMap<i32, SfaController>,
    pub snapshot: HashMap<i32, SnapshotRecord>,
    pub snapshot_interval: HashMap<i32, SnapshotInterval>,
    pub snapshot_retention: HashMap<i32, SnapshotRetention>,
    pub stratagem_config: HashMap<i32, StratagemConfiguration>,
    pub target: HashMap<i32, TargetRecord>,
    pub user: HashMap<i32, AuthUserRecord>,
    pub user_group: HashMap<i32, AuthUserGroupRecord>,
}

#[derive(Default, PartialEq, Clone, Debug)]
pub struct ArcCache {
    pub corosync_resource: HashMap<i32, Arc<CorosyncResourceRecord>>,
    pub corosync_resource_ban: HashMap<i32, Arc<CorosyncResourceBanRecord>>,
    pub active_alert: HashMap<i32, Arc<AlertState>>,
    pub filesystem: HashMap<i32, Arc<Filesystem>>,
    pub group: HashMap<i32, Arc<AuthGroupRecord>>,
    pub host: HashMap<i32, Arc<Host>>,
    pub lnet: HashMap<i32, Arc<Lnet>>,
    pub ost_pool: HashMap<i32, Arc<OstPoolRecord>>,
    pub ost_pool_osts: HashMap<i32, Arc<OstPoolOstsRecord>>,
    pub sfa_disk_drive: HashMap<i32, Arc<SfaDiskDrive>>,
    pub sfa_enclosure: HashMap<i32, Arc<SfaEnclosure>>,
    pub sfa_storage_system: HashMap<i32, Arc<SfaStorageSystem>>,
    pub sfa_job: HashMap<i32, Arc<SfaJob>>,
    pub sfa_power_supply: HashMap<i32, Arc<SfaPowerSupply>>,
    pub sfa_controller: HashMap<i32, Arc<SfaController>>,
    pub snapshot: HashMap<i32, Arc<SnapshotRecord>>,
    pub snapshot_interval: HashMap<i32, Arc<SnapshotInterval>>,
    pub snapshot_retention: HashMap<i32, Arc<SnapshotRetention>>,
    pub stratagem_config: HashMap<i32, Arc<StratagemConfiguration>>,
    pub target: HashMap<i32, Arc<TargetRecord>>,
    pub user: HashMap<i32, Arc<AuthUserRecord>>,
    pub user_group: HashMap<i32, Arc<AuthUserGroupRecord>>,
}

impl Cache {
    /// Removes the record from the cache
    pub fn remove_record(&mut self, x: RecordId) -> Option<Record> {
        match x {
            RecordId::ActiveAlert(id) => self.active_alert.remove(&id).map(Record::ActiveAlert),
            RecordId::CorosyncResource(id) => self
                .corosync_resource
                .remove(&id)
                .map(Record::CorosyncResource),
            RecordId::CorosyncResourceBan(id) => self
                .corosync_resource_ban
                .remove(&id)
                .map(Record::CorosyncResourceBan),
            RecordId::Filesystem(id) => self.filesystem.remove(&id).map(Record::Filesystem),
            RecordId::Group(id) => self.group.remove(&id).map(Record::Group),
            RecordId::Host(id) => self.host.remove(&id).map(Record::Host),
            RecordId::Lnet(id) => self.lnet.remove(&id).map(Record::Lnet),
            RecordId::OstPool(id) => self.ost_pool.remove(&id).map(Record::OstPool),
            RecordId::OstPoolOsts(id) => self.ost_pool_osts.remove(&id).map(Record::OstPoolOsts),
            RecordId::SfaDiskDrive(id) => self.sfa_disk_drive.remove(&id).map(Record::SfaDiskDrive),
            RecordId::SfaEnclosure(id) => self.sfa_enclosure.remove(&id).map(Record::SfaEnclosure),
            RecordId::SfaStorageSystem(id) => self
                .sfa_storage_system
                .remove(&id)
                .map(Record::SfaStorageSystem),
            RecordId::SfaJob(id) => self.sfa_job.remove(&id).map(Record::SfaJob),
            RecordId::SfaPowerSupply(id) => self
                .sfa_power_supply
                .remove(&id)
                .map(Record::SfaPowerSupply),
            RecordId::SfaController(id) => {
                self.sfa_controller.remove(&id).map(Record::SfaController)
            }
            RecordId::StratagemConfig(id) => self
                .stratagem_config
                .remove(&id)
                .map(Record::StratagemConfig),
            RecordId::Snapshot(id) => self.snapshot.remove(&id).map(Record::Snapshot),
            RecordId::SnapshotInterval(id) => self
                .snapshot_interval
                .remove(&id)
                .map(Record::SnapshotInterval),
            RecordId::SnapshotRetention(id) => self
                .snapshot_retention
                .remove(&id)
                .map(Record::SnapshotRetention),
            RecordId::Target(id) => self.target.remove(&id).map(Record::Target),
            RecordId::User(id) => self.user.remove(&id).map(Record::User),
            RecordId::UserGroup(id) => self.user_group.remove(&id).map(Record::UserGroup),
        }
    }
    /// Inserts the record into the cache
    pub fn insert_record(&mut self, x: Record) {
        match x {
            Record::ActiveAlert(x) => {
                self.active_alert.insert(x.id, x);
            }
            Record::CorosyncResource(x) => {
                self.corosync_resource.insert(x.id, x);
            }
            Record::CorosyncResourceBan(x) => {
                self.corosync_resource_ban.insert(x.id, x);
            }
            Record::Filesystem(x) => {
                self.filesystem.insert(x.id, x);
            }
            Record::Host(x) => {
                self.host.insert(x.id, x);
            }
            Record::Group(x) => {
                self.group.insert(x.id, x);
            }
            Record::Lnet(x) => {
                self.lnet.insert(x.id(), x);
            }
            Record::OstPool(x) => {
                self.ost_pool.insert(x.id(), x);
            }
            Record::OstPoolOsts(x) => {
                self.ost_pool_osts.insert(x.id(), x);
            }
            Record::SfaDiskDrive(x) => {
                self.sfa_disk_drive.insert(x.id(), x);
            }
            Record::SfaEnclosure(x) => {
                self.sfa_enclosure.insert(x.id(), x);
            }
            Record::SfaStorageSystem(x) => {
                self.sfa_storage_system.insert(x.id(), x);
            }
            Record::SfaJob(x) => {
                self.sfa_job.insert(x.id(), x);
            }
            Record::SfaPowerSupply(x) => {
                self.sfa_power_supply.insert(x.id, x);
            }
            Record::SfaController(x) => {
                self.sfa_controller.insert(x.id, x);
            }
            Record::Snapshot(x) => {
                self.snapshot.insert(x.id, x);
            }
            Record::SnapshotInterval(x) => {
                self.snapshot_interval.insert(x.id(), x);
            }
            Record::SnapshotRetention(x) => {
                self.snapshot_retention.insert(x.id(), x);
            }
            Record::StratagemConfig(x) => {
                self.stratagem_config.insert(x.id(), x);
            }
            Record::Target(x) => {
                self.target.insert(x.id, x);
            }
            Record::User(x) => {
                self.user.insert(x.id, x);
            }
            Record::UserGroup(x) => {
                self.user_group.insert(x.id, x);
            }
        }
    }
}

/// A `Record` with it's concrete type erased.
/// The returned item implements the `Label` and `EndpointName`
/// traits.
pub trait ErasedRecord: Label + Id + fmt::Debug {}
impl<T: Label + Id + ToCompositeId + fmt::Debug> ErasedRecord for T {}

fn erase(x: Arc<impl ErasedRecord + 'static>) -> Arc<dyn ErasedRecord> {
    x
}

impl ArcCache {
    /// Removes the record from the arc cache
    pub fn remove_record(&mut self, x: RecordId) -> bool {
        match x {
            RecordId::ActiveAlert(id) => self.active_alert.remove(&id).is_some(),
            RecordId::CorosyncResource(id) => self.corosync_resource.remove(&id).is_some(),
            RecordId::CorosyncResourceBan(id) => self.corosync_resource_ban.remove(&id).is_some(),
            RecordId::Filesystem(id) => self.filesystem.remove(&id).is_some(),
            RecordId::Group(id) => self.group.remove(&id).is_some(),
            RecordId::Host(id) => self.host.remove(&id).is_some(),
            RecordId::Lnet(id) => self.lnet.remove(&id).is_some(),
            RecordId::OstPool(id) => self.ost_pool.remove(&id).is_some(),
            RecordId::OstPoolOsts(id) => self.ost_pool_osts.remove(&id).is_some(),
            RecordId::SfaDiskDrive(id) => self.sfa_disk_drive.remove(&id).is_some(),
            RecordId::SfaEnclosure(id) => self.sfa_enclosure.remove(&id).is_some(),
            RecordId::SfaStorageSystem(id) => self.sfa_storage_system.remove(&id).is_some(),
            RecordId::SfaJob(id) => self.sfa_job.remove(&id).is_some(),
            RecordId::SfaPowerSupply(id) => self.sfa_power_supply.remove(&id).is_some(),
            RecordId::SfaController(id) => self.sfa_controller.remove(&id).is_some(),
            RecordId::Snapshot(id) => self.snapshot.remove(&id).is_some(),
            RecordId::SnapshotInterval(id) => self.snapshot_interval.remove(&id).is_some(),
            RecordId::SnapshotRetention(id) => self.snapshot_retention.remove(&id).is_some(),
            RecordId::StratagemConfig(id) => self.stratagem_config.remove(&id).is_some(),
            RecordId::Target(id) => self.target.remove(&id).is_some(),
            RecordId::User(id) => self.user.remove(&id).is_some(),
            RecordId::UserGroup(id) => self.user_group.remove(&id).is_some(),
        }
    }
    /// Inserts the record into the cache
    pub fn insert_record(&mut self, x: Record) {
        match x {
            Record::ActiveAlert(x) => {
                self.active_alert.insert(x.id, Arc::new(x));
            }
            Record::CorosyncResource(x) => {
                self.corosync_resource.insert(x.id, Arc::new(x));
            }
            Record::CorosyncResourceBan(x) => {
                self.corosync_resource_ban.insert(x.id, Arc::new(x));
            }
            Record::Filesystem(x) => {
                self.filesystem.insert(x.id, Arc::new(x));
            }
            Record::Group(x) => {
                self.group.insert(x.id, Arc::new(x));
            }
            Record::Host(x) => {
                self.host.insert(x.id, Arc::new(x));
            }
            Record::Lnet(x) => {
                self.lnet.insert(x.id(), Arc::new(x));
            }
            Record::OstPool(x) => {
                self.ost_pool.insert(x.id(), Arc::new(x));
            }
            Record::OstPoolOsts(x) => {
                self.ost_pool_osts.insert(x.id(), Arc::new(x));
            }
            Record::SfaDiskDrive(x) => {
                self.sfa_disk_drive.insert(x.id(), Arc::new(x));
            }
            Record::SfaEnclosure(x) => {
                self.sfa_enclosure.insert(x.id(), Arc::new(x));
            }
            Record::SfaStorageSystem(x) => {
                self.sfa_storage_system.insert(x.id(), Arc::new(x));
            }
            Record::SfaJob(x) => {
                self.sfa_job.insert(x.id(), Arc::new(x));
            }
            Record::SfaPowerSupply(x) => {
                self.sfa_power_supply.insert(x.id(), Arc::new(x));
            }
            Record::SfaController(x) => {
                self.sfa_controller.insert(x.id(), Arc::new(x));
            }
            Record::Snapshot(x) => {
                self.snapshot.insert(x.id, Arc::new(x));
            }
            Record::SnapshotInterval(x) => {
                self.snapshot_interval.insert(x.id, Arc::new(x));
            }
            Record::SnapshotRetention(x) => {
                self.snapshot_retention.insert(x.id(), Arc::new(x));
            }
            Record::StratagemConfig(x) => {
                self.stratagem_config.insert(x.id(), Arc::new(x));
            }
            Record::Target(x) => {
                self.target.insert(x.id, Arc::new(x));
            }
            Record::User(x) => {
                self.user.insert(x.id, Arc::new(x));
            }
            Record::UserGroup(x) => {
                self.user_group.insert(x.id, Arc::new(x));
            }
        }
    }
    /// Given a `CompositeId`, returns an `ErasedRecord` if
    /// a matching one exists.
    pub fn get_erased_record(&self, composite_id: &CompositeId) -> Option<Arc<dyn ErasedRecord>> {
        match &composite_id.0 {
            ComponentType::Filesystem => self.filesystem.get(&composite_id.1).cloned().map(erase),
            ComponentType::Host => self.host.get(&composite_id.1).cloned().map(erase),
            ComponentType::Lnet => self.lnet.get(&composite_id.1).cloned().map(erase),
            ComponentType::Target => self.target.get(&composite_id.1).cloned().map(erase),
        }
    }
}

impl From<&Cache> for ArcCache {
    fn from(cache: &Cache) -> Self {
        Self {
            corosync_resource: hashmap_to_arc_hashmap(&cache.corosync_resource),
            corosync_resource_ban: hashmap_to_arc_hashmap(&cache.corosync_resource_ban),
            active_alert: hashmap_to_arc_hashmap(&cache.active_alert),
            filesystem: hashmap_to_arc_hashmap(&cache.filesystem),
            group: hashmap_to_arc_hashmap(&cache.group),
            host: hashmap_to_arc_hashmap(&cache.host),
            lnet: hashmap_to_arc_hashmap(&cache.lnet),
            ost_pool: hashmap_to_arc_hashmap(&cache.ost_pool),
            ost_pool_osts: hashmap_to_arc_hashmap(&cache.ost_pool_osts),
            sfa_disk_drive: hashmap_to_arc_hashmap(&cache.sfa_disk_drive),
            sfa_enclosure: hashmap_to_arc_hashmap(&cache.sfa_enclosure),
            sfa_storage_system: hashmap_to_arc_hashmap(&cache.sfa_storage_system),
            sfa_job: hashmap_to_arc_hashmap(&cache.sfa_job),
            sfa_power_supply: hashmap_to_arc_hashmap(&cache.sfa_power_supply),
            sfa_controller: hashmap_to_arc_hashmap(&cache.sfa_controller),
            snapshot: hashmap_to_arc_hashmap(&cache.snapshot),
            snapshot_interval: hashmap_to_arc_hashmap(&cache.snapshot_interval),
            snapshot_retention: hashmap_to_arc_hashmap(&cache.snapshot_retention),
            stratagem_config: hashmap_to_arc_hashmap(&cache.stratagem_config),
            target: hashmap_to_arc_hashmap(&cache.target),
            user: hashmap_to_arc_hashmap(&cache.user),
            user_group: hashmap_to_arc_hashmap(&cache.user_group),
        }
    }
}

impl From<&ArcCache> for Cache {
    fn from(cache: &ArcCache) -> Self {
        Self {
            corosync_resource: arc_hashmap_to_hashmap(&cache.corosync_resource),
            corosync_resource_ban: arc_hashmap_to_hashmap(&cache.corosync_resource_ban),
            active_alert: arc_hashmap_to_hashmap(&cache.active_alert),
            filesystem: arc_hashmap_to_hashmap(&cache.filesystem),
            group: arc_hashmap_to_hashmap(&cache.group),
            host: arc_hashmap_to_hashmap(&cache.host),
            lnet: arc_hashmap_to_hashmap(&cache.lnet),
            ost_pool: arc_hashmap_to_hashmap(&cache.ost_pool),
            ost_pool_osts: arc_hashmap_to_hashmap(&cache.ost_pool_osts),
            sfa_disk_drive: arc_hashmap_to_hashmap(&cache.sfa_disk_drive),
            sfa_enclosure: arc_hashmap_to_hashmap(&cache.sfa_enclosure),
            sfa_storage_system: arc_hashmap_to_hashmap(&cache.sfa_storage_system),
            sfa_job: arc_hashmap_to_hashmap(&cache.sfa_job),
            sfa_power_supply: arc_hashmap_to_hashmap(&cache.sfa_power_supply),
            sfa_controller: arc_hashmap_to_hashmap(&cache.sfa_controller),
            snapshot: arc_hashmap_to_hashmap(&cache.snapshot),
            snapshot_interval: arc_hashmap_to_hashmap(&cache.snapshot_interval),
            snapshot_retention: arc_hashmap_to_hashmap(&cache.snapshot_retention),
            stratagem_config: arc_hashmap_to_hashmap(&cache.stratagem_config),
            target: arc_hashmap_to_hashmap(&cache.target),
            user: arc_hashmap_to_hashmap(&cache.user),
            user_group: arc_hashmap_to_hashmap(&cache.user_group),
        }
    }
}

#[allow(clippy::large_enum_variant)]
#[derive(serde::Serialize, serde::Deserialize, Debug, Clone, PartialEq)]
#[serde(tag = "tag", content = "payload")]
pub enum Record {
    ActiveAlert(AlertState),
    CorosyncResource(CorosyncResourceRecord),
    CorosyncResourceBan(CorosyncResourceBanRecord),
    Filesystem(Filesystem),
    Group(AuthGroupRecord),
    Host(Host),
    Lnet(Lnet),
    OstPool(OstPoolRecord),
    OstPoolOsts(OstPoolOstsRecord),
    SfaDiskDrive(SfaDiskDrive),
    SfaEnclosure(SfaEnclosure),
    SfaStorageSystem(SfaStorageSystem),
    SfaJob(SfaJob),
    SfaPowerSupply(SfaPowerSupply),
    SfaController(SfaController),
    Snapshot(SnapshotRecord),
    SnapshotInterval(SnapshotInterval),
    SnapshotRetention(SnapshotRetention),
    StratagemConfig(StratagemConfiguration),
    Target(TargetRecord),
    User(AuthUserRecord),
    UserGroup(AuthUserGroupRecord),
}

#[derive(Debug, Clone)]
pub enum ArcRecord {
    ActiveAlert(Arc<AlertState>),
    CorosyncResource(Arc<CorosyncResourceRecord>),
    CorosyncResourceBan(Arc<CorosyncResourceBanRecord>),
    Filesystem(Arc<Filesystem>),
    Group(Arc<AuthGroupRecord>),
    Host(Arc<Host>),
    Lnet(Arc<Lnet>),
    OstPool(Arc<OstPoolRecord>),
    OstPoolOsts(Arc<OstPoolOstsRecord>),
    SfaDiskDrive(Arc<SfaDiskDrive>),
    SfaEnclosure(Arc<SfaEnclosure>),
    SfaStorageSystem(Arc<SfaStorageSystem>),
    SfaJob(Arc<SfaJob>),
    SfaPowerSupply(Arc<SfaPowerSupply>),
    SfaController(Arc<SfaController>),
    Snapshot(Arc<SnapshotRecord>),
    SnapshotInterval(Arc<SnapshotInterval>),
    SnapshotRetention(Arc<SnapshotRetention>),
    StratagemConfig(Arc<StratagemConfiguration>),
    Target(Arc<TargetRecord>),
    User(Arc<AuthUserRecord>),
    UserGroup(Arc<AuthUserGroupRecord>),
}

impl From<Record> for ArcRecord {
    fn from(record: Record) -> Self {
        match record {
            Record::ActiveAlert(x) => Self::ActiveAlert(Arc::new(x)),
            Record::CorosyncResource(x) => Self::CorosyncResource(Arc::new(x)),
            Record::CorosyncResourceBan(x) => Self::CorosyncResourceBan(Arc::new(x)),
            Record::Filesystem(x) => Self::Filesystem(Arc::new(x)),
            Record::Group(x) => Self::Group(Arc::new(x)),
            Record::Host(x) => Self::Host(Arc::new(x)),
            Record::Lnet(x) => Self::Lnet(Arc::new(x)),
            Record::OstPool(x) => Self::OstPool(Arc::new(x)),
            Record::OstPoolOsts(x) => Self::OstPoolOsts(Arc::new(x)),
            Record::SfaDiskDrive(x) => Self::SfaDiskDrive(Arc::new(x)),
            Record::SfaEnclosure(x) => Self::SfaEnclosure(Arc::new(x)),
            Record::SfaStorageSystem(x) => Self::SfaStorageSystem(Arc::new(x)),
            Record::SfaJob(x) => Self::SfaJob(Arc::new(x)),
            Record::SfaPowerSupply(x) => Self::SfaPowerSupply(Arc::new(x)),
            Record::SfaController(x) => Self::SfaController(Arc::new(x)),
            Record::StratagemConfig(x) => Self::StratagemConfig(Arc::new(x)),
            Record::Snapshot(x) => Self::Snapshot(Arc::new(x)),
            Record::SnapshotInterval(x) => Self::SnapshotInterval(Arc::new(x)),
            Record::SnapshotRetention(x) => Self::SnapshotRetention(Arc::new(x)),
            Record::Target(x) => Self::Target(Arc::new(x)),
            Record::User(x) => Self::User(Arc::new(x)),
            Record::UserGroup(x) => Self::UserGroup(Arc::new(x)),
        }
    }
}

#[derive(Clone, Copy, Debug, Hash, PartialEq, Eq, serde::Deserialize, serde::Serialize)]
#[serde(tag = "tag", content = "payload")]
pub enum RecordId {
    ActiveAlert(i32),
    CorosyncResource(i32),
    CorosyncResourceBan(i32),
    Filesystem(i32),
    Group(i32),
    Host(i32),
    Lnet(i32),
    OstPool(i32),
    OstPoolOsts(i32),
    SfaDiskDrive(i32),
    SfaEnclosure(i32),
    SfaStorageSystem(i32),
    SfaJob(i32),
    SfaPowerSupply(i32),
    SfaController(i32),
    StratagemConfig(i32),
    Snapshot(i32),
    SnapshotInterval(i32),
    SnapshotRetention(i32),
    Target(i32),
    User(i32),
    UserGroup(i32),
}

impl From<&Record> for RecordId {
    fn from(record: &Record) -> Self {
        match record {
            Record::ActiveAlert(x) => RecordId::ActiveAlert(x.id),
            Record::CorosyncResource(x) => RecordId::CorosyncResource(x.id),
            Record::CorosyncResourceBan(x) => RecordId::CorosyncResourceBan(x.id),
            Record::Filesystem(x) => RecordId::Filesystem(x.id),
            Record::Group(x) => RecordId::Group(x.id),
            Record::Host(x) => RecordId::Host(x.id),
            Record::Lnet(x) => RecordId::Lnet(x.id),
            Record::OstPool(x) => RecordId::OstPool(x.id),
            Record::OstPoolOsts(x) => RecordId::OstPoolOsts(x.id),
            Record::SfaDiskDrive(x) => RecordId::SfaDiskDrive(x.id),
            Record::SfaEnclosure(x) => RecordId::SfaEnclosure(x.id),
            Record::SfaStorageSystem(x) => RecordId::SfaStorageSystem(x.id),
            Record::SfaJob(x) => RecordId::SfaJob(x.id),
            Record::SfaPowerSupply(x) => RecordId::SfaPowerSupply(x.id),
            Record::SfaController(x) => RecordId::SfaController(x.id),
            Record::StratagemConfig(x) => RecordId::StratagemConfig(x.id),
            Record::Snapshot(x) => RecordId::Snapshot(x.id),
            Record::SnapshotInterval(x) => RecordId::SnapshotInterval(x.id),
            Record::SnapshotRetention(x) => RecordId::SnapshotRetention(x.id),
            Record::Target(x) => RecordId::Target(x.id),
            Record::User(x) => RecordId::User(x.id),
            Record::UserGroup(x) => RecordId::UserGroup(x.id),
        }
    }
}

impl Deref for RecordId {
    type Target = i32;

    fn deref(&self) -> &i32 {
        match self {
            Self::ActiveAlert(x)
            | Self::CorosyncResource(x)
            | Self::CorosyncResourceBan(x)
            | Self::Filesystem(x)
            | Self::Group(x)
            | Self::Host(x)
            | Self::OstPool(x)
            | Self::OstPoolOsts(x)
            | Self::SfaDiskDrive(x)
            | Self::SfaEnclosure(x)
            | Self::SfaStorageSystem(x)
            | Self::SfaJob(x)
            | Self::SfaPowerSupply(x)
            | Self::SfaController(x)
            | Self::Snapshot(x)
            | Self::StratagemConfig(x)
            | Self::SnapshotInterval(x)
            | Self::SnapshotRetention(x)
            | Self::Target(x)
            | Self::User(x)
            | Self::UserGroup(x)
            | Self::Lnet(x) => x,
        }
    }
}

#[allow(clippy::large_enum_variant)]
#[derive(Debug, serde::Serialize, serde::Deserialize, Clone)]
#[serde(tag = "tag", content = "payload")]
pub enum RecordChange {
    Update(Record),
    Delete(RecordId),
}

/// Message variants.
#[allow(clippy::large_enum_variant)]
#[derive(serde::Serialize, serde::Deserialize, Clone, Debug)]
#[serde(tag = "tag", content = "payload")]
pub enum Message {
    Records(Cache),
    RecordChange(RecordChange),
}

#[cfg(test)]
mod tests {
    use crate::{
        warp_drive::{ArcCache, ArcValuesExt, Cache},
        OstPoolOstsRecord, OstPoolRecord,
    };
    use std::sync::Arc;

    #[test]
    fn test_cache_conversions() {
        let c0: Cache = get_cache();
        let c1: ArcCache = (&c0).into(); // From<&Cache> for ArcCache
        let c0_again: Cache = (&c1).into(); // From<&ArcCache> for Cache

        let mut c2: ArcCache = c1.clone();
        let mut c3: ArcCache = c2.clone();

        let rec1 = Arc::new(OstPoolOstsRecord {
            id: 1,
            ostpool_id: 1,
            ost_id: 1,
        });
        let rec2 = Arc::new(OstPoolOstsRecord {
            id: 2,
            ostpool_id: 2,
            ost_id: 2,
        });
        let rec18 = Arc::clone(&c1.ost_pool_osts.get(&18).unwrap());
        let rec19 = Arc::clone(&c1.ost_pool_osts.get(&19).unwrap());

        c2.ost_pool_osts.insert(1, Arc::clone(&rec1));
        c3.ost_pool_osts.insert(2, Arc::clone(&rec2));

        // The entries to c2 and c3 are added independently despite sharing the same "body"
        assert_eq!(
            c1.ost_pool_osts,
            im::hashmap!(18 => Arc::clone(&rec18), 19 => Arc::clone(&rec19))
        );
        assert_eq!(
            c2.ost_pool_osts,
            im::hashmap!(18 => Arc::clone(&rec18), 19 => Arc::clone(&rec19), 1 => rec1)
        );
        assert_eq!(
            c3.ost_pool_osts,
            im::hashmap!(18 => Arc::clone(&rec18), 19 => Arc::clone(&rec19), 2 => rec2)
        );
        // the original cache and the cache - conversion result - should be equal
        assert_eq!(c0, c0_again);
    }

    #[test]
    fn test_arc_values() {
        let cache: ArcCache = (&get_cache()).into();

        let osts: Vec<&OstPoolOstsRecord> = cache.ost_pool_osts.values().map(|x| &**x).collect();
        let osts2: Vec<&OstPoolOstsRecord> = cache.ost_pool_osts.arc_values().collect();
        assert_eq!(osts, osts2);
    }

    fn get_cache() -> Cache {
        let mut cache: Cache = Default::default();
        cache.ost_pool.insert(
            18,
            OstPoolRecord {
                id: 18,
                name: "pool".to_string(),
                filesystem_id: 1,
            },
        );
        cache.ost_pool_osts.insert(
            18,
            OstPoolOstsRecord {
                id: 18,
                ostpool_id: 18,
                ost_id: 13,
            },
        );
        cache.ost_pool_osts.insert(
            19,
            OstPoolOstsRecord {
                id: 19,
                ostpool_id: 18,
                ost_id: 14,
            },
        );
        cache
    }
}
