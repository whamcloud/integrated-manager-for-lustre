// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    db::{
        AuthGroupRecord, AuthUserGroupRecord, AuthUserRecord, ContentTypeRecord,
        CorosyncConfigurationRecord, Id, LnetConfigurationRecord, ManagedTargetMountRecord,
        OstPoolOstsRecord, OstPoolRecord, PacemakerConfigurationRecord, StratagemConfiguration,
        VolumeNodeRecord, VolumeRecord,
    },
    Alert, CompositeId, EndpointNameSelf, Filesystem, Host, Label, LockChange, Target,
    TargetConfParam, ToCompositeId,
};
use im::{HashMap, HashSet};
use std::{
    hash::{BuildHasher, Hash},
    iter::FusedIterator,
    ops::Deref,
    sync::Arc,
};

/// This trait is to bring method `arc_values()` to the collections of
/// type HashMap<K, Arc<V>> to simplify iterating through the values.
/// Example:
/// ```rust,norun
///     use std::sync::Arc;
///     use im::HashMap;
///     use iml_wire_types::warp_drive::ArcValuesExt;
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

/// The current state of locks based on data from the locks queue
pub type Locks = HashMap<String, HashSet<LockChange>>;

#[derive(serde::Serialize, serde::Deserialize, Default, PartialEq, Clone, Debug)]
pub struct Cache {
    pub content_type: HashMap<u32, ContentTypeRecord>,
    pub corosync_configuration: HashMap<u32, CorosyncConfigurationRecord>,
    pub active_alert: HashMap<u32, Alert>,
    pub filesystem: HashMap<u32, Filesystem>,
    pub group: HashMap<u32, AuthGroupRecord>,
    pub host: HashMap<u32, Host>,
    pub lnet_configuration: HashMap<u32, LnetConfigurationRecord>,
    pub managed_target_mount: HashMap<u32, ManagedTargetMountRecord>,
    pub ost_pool: HashMap<u32, OstPoolRecord>,
    pub ost_pool_osts: HashMap<u32, OstPoolOstsRecord>,
    pub stratagem_config: HashMap<u32, StratagemConfiguration>,
    pub target: HashMap<u32, Target<TargetConfParam>>,
    pub user: HashMap<u32, AuthUserRecord>,
    pub user_group: HashMap<u32, AuthUserGroupRecord>,
    pub pacemaker_configuration: HashMap<u32, PacemakerConfigurationRecord>,
    pub volume: HashMap<u32, VolumeRecord>,
    pub volume_node: HashMap<u32, VolumeNodeRecord>,
}

#[derive(Default, PartialEq, Clone, Debug)]
pub struct ArcCache {
    pub content_type: HashMap<u32, Arc<ContentTypeRecord>>,
    pub corosync_configuration: HashMap<u32, Arc<CorosyncConfigurationRecord>>,
    pub active_alert: HashMap<u32, Arc<Alert>>,
    pub filesystem: HashMap<u32, Arc<Filesystem>>,
    pub group: HashMap<u32, Arc<AuthGroupRecord>>,
    pub host: HashMap<u32, Arc<Host>>,
    pub lnet_configuration: HashMap<u32, Arc<LnetConfigurationRecord>>,
    pub managed_target_mount: HashMap<u32, Arc<ManagedTargetMountRecord>>,
    pub ost_pool: HashMap<u32, Arc<OstPoolRecord>>,
    pub ost_pool_osts: HashMap<u32, Arc<OstPoolOstsRecord>>,
    pub pacemaker_configuration: HashMap<u32, Arc<PacemakerConfigurationRecord>>,
    pub stratagem_config: HashMap<u32, Arc<StratagemConfiguration>>,
    pub target: HashMap<u32, Arc<Target<TargetConfParam>>>,
    pub user: HashMap<u32, Arc<AuthUserRecord>>,
    pub user_group: HashMap<u32, Arc<AuthUserGroupRecord>>,
    pub volume: HashMap<u32, Arc<VolumeRecord>>,
    pub volume_node: HashMap<u32, Arc<VolumeNodeRecord>>,
}

impl Cache {
    /// Removes the record from the cache
    pub fn remove_record(&mut self, x: RecordId) -> bool {
        match x {
            RecordId::ActiveAlert(id) => self.active_alert.remove(&id).is_some(),
            RecordId::CorosyncConfiguration(id) => {
                self.corosync_configuration.remove(&id).is_some()
            }
            RecordId::Filesystem(id) => self.filesystem.remove(&id).is_some(),
            RecordId::Group(id) => self.group.remove(&id).is_some(),
            RecordId::Host(id) => self.host.remove(&id).is_some(),
            RecordId::LnetConfiguration(id) => self.lnet_configuration.remove(&id).is_some(),
            RecordId::ContentType(id) => self.content_type.remove(&id).is_some(),
            RecordId::ManagedTargetMount(id) => self.managed_target_mount.remove(&id).is_some(),
            RecordId::OstPool(id) => self.ost_pool.remove(&id).is_some(),
            RecordId::OstPoolOsts(id) => self.ost_pool_osts.remove(&id).is_some(),
            RecordId::PacemakerConfiguration(id) => {
                self.pacemaker_configuration.remove(&id).is_some()
            }
            RecordId::StratagemConfig(id) => self.stratagem_config.remove(&id).is_some(),
            RecordId::Target(id) => self.target.remove(&id).is_some(),
            RecordId::User(id) => self.user.remove(&id).is_some(),
            RecordId::UserGroup(id) => self.user_group.remove(&id).is_some(),
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
            Record::CorosyncConfiguration(x) => {
                self.corosync_configuration.insert(x.id, x);
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
            Record::ContentType(x) => {
                self.content_type.insert(x.id(), x);
            }
            Record::LnetConfiguration(x) => {
                self.lnet_configuration.insert(x.id(), x);
            }
            Record::ManagedTargetMount(x) => {
                self.managed_target_mount.insert(x.id(), x);
            }
            Record::OstPool(x) => {
                self.ost_pool.insert(x.id(), x);
            }
            Record::OstPoolOsts(x) => {
                self.ost_pool_osts.insert(x.id(), x);
            }
            Record::PacemakerConfiguration(x) => {
                self.pacemaker_configuration.insert(x.id, x);
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
            Record::Volume(x) => {
                self.volume.insert(x.id, x);
            }
            Record::VolumeNode(x) => {
                self.volume_node.insert(x.id(), x);
            }
        }
    }
}

/// A `Record` with it's concrete type erased.
/// The returned item implements the `Label` and `EndpointName`
/// traits.
pub trait ErasedRecord: Label + EndpointNameSelf + Id + core::fmt::Debug {}
impl<T: Label + EndpointNameSelf + Id + ToCompositeId + core::fmt::Debug> ErasedRecord for T {}

fn erase(x: Arc<impl ErasedRecord + 'static>) -> Arc<dyn ErasedRecord> {
    x
}

impl ArcCache {
    /// Removes the record from the arc cache
    pub fn remove_record(&mut self, x: RecordId) -> bool {
        match x {
            RecordId::ActiveAlert(id) => self.active_alert.remove(&id).is_some(),
            RecordId::CorosyncConfiguration(id) => {
                self.corosync_configuration.remove(&id).is_some()
            }
            RecordId::Filesystem(id) => self.filesystem.remove(&id).is_some(),
            RecordId::Group(id) => self.group.remove(&id).is_some(),
            RecordId::Host(id) => self.host.remove(&id).is_some(),
            RecordId::ContentType(id) => self.content_type.remove(&id).is_some(),
            RecordId::LnetConfiguration(id) => self.lnet_configuration.remove(&id).is_some(),
            RecordId::ManagedTargetMount(id) => self.managed_target_mount.remove(&id).is_some(),
            RecordId::OstPool(id) => self.ost_pool.remove(&id).is_some(),
            RecordId::OstPoolOsts(id) => self.ost_pool_osts.remove(&id).is_some(),
            RecordId::PacemakerConfiguration(id) => {
                self.pacemaker_configuration.remove(&id).is_some()
            }
            RecordId::StratagemConfig(id) => self.stratagem_config.remove(&id).is_some(),
            RecordId::Target(id) => self.target.remove(&id).is_some(),
            RecordId::User(id) => self.user.remove(&id).is_some(),
            RecordId::UserGroup(id) => self.user_group.remove(&id).is_some(),
            RecordId::Volume(id) => self.volume.remove(&id).is_some(),
            RecordId::VolumeNode(id) => self.volume_node.remove(&id).is_some(),
        }
    }
    /// Inserts the record into the cache
    pub fn insert_record(&mut self, x: Record) {
        match x {
            Record::ActiveAlert(x) => {
                self.active_alert.insert(x.id, Arc::new(x));
            }
            Record::CorosyncConfiguration(x) => {
                self.corosync_configuration.insert(x.id, Arc::new(x));
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
            Record::ContentType(x) => {
                self.content_type.insert(x.id(), Arc::new(x));
            }
            Record::LnetConfiguration(x) => {
                self.lnet_configuration.insert(x.id(), Arc::new(x));
            }
            Record::ManagedTargetMount(x) => {
                self.managed_target_mount.insert(x.id(), Arc::new(x));
            }
            Record::OstPool(x) => {
                self.ost_pool.insert(x.id(), Arc::new(x));
            }
            Record::OstPoolOsts(x) => {
                self.ost_pool_osts.insert(x.id(), Arc::new(x));
            }
            Record::PacemakerConfiguration(x) => {
                self.pacemaker_configuration.insert(x.id, Arc::new(x));
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
            Record::Volume(x) => {
                self.volume.insert(x.id, Arc::new(x));
            }
            Record::VolumeNode(x) => {
                self.volume_node.insert(x.id(), Arc::new(x));
            }
        }
    }
    /// Given a `CompositeId`, returns an `ErasedRecord` if
    /// a matching one exists.
    pub fn get_erased_record(&self, composite_id: &CompositeId) -> Option<Arc<dyn ErasedRecord>> {
        let content_type = self.content_type.get(&composite_id.0)?;

        match content_type.model.as_ref() {
            "managedfilesystem" => self.filesystem.get(&composite_id.1).cloned().map(erase),
            "managedhost" => self.host.get(&composite_id.1).cloned().map(erase),
            "lnetconfiguration" => self
                .lnet_configuration
                .get(&composite_id.1)
                .cloned()
                .map(erase),
            "pacemakerconfiguration" => self
                .pacemaker_configuration
                .get(&composite_id.1)
                .cloned()
                .map(erase),
            "corosync2configuration" => self
                .corosync_configuration
                .get(&composite_id.1)
                .cloned()
                .map(erase),
            "managedtarget" | "managedost" | "managedmdt" | "managedmgt" | "managedmgs" => {
                self.target.get(&composite_id.1).cloned().map(erase)
            }
            _ => None,
        }
    }
}

impl From<&Cache> for ArcCache {
    fn from(cache: &Cache) -> Self {
        Self {
            content_type: hashmap_to_arc_hashmap(&cache.content_type),
            corosync_configuration: hashmap_to_arc_hashmap(&cache.corosync_configuration),
            active_alert: hashmap_to_arc_hashmap(&cache.active_alert),
            filesystem: hashmap_to_arc_hashmap(&cache.filesystem),
            group: hashmap_to_arc_hashmap(&cache.group),
            host: hashmap_to_arc_hashmap(&cache.host),
            lnet_configuration: hashmap_to_arc_hashmap(&cache.lnet_configuration),
            managed_target_mount: hashmap_to_arc_hashmap(&cache.managed_target_mount),
            ost_pool: hashmap_to_arc_hashmap(&cache.ost_pool),
            ost_pool_osts: hashmap_to_arc_hashmap(&cache.ost_pool_osts),
            pacemaker_configuration: hashmap_to_arc_hashmap(&cache.pacemaker_configuration),
            stratagem_config: hashmap_to_arc_hashmap(&cache.stratagem_config),
            target: hashmap_to_arc_hashmap(&cache.target),
            user: hashmap_to_arc_hashmap(&cache.user),
            user_group: hashmap_to_arc_hashmap(&cache.user_group),
            volume: hashmap_to_arc_hashmap(&cache.volume),
            volume_node: hashmap_to_arc_hashmap(&cache.volume_node),
        }
    }
}

impl From<&ArcCache> for Cache {
    fn from(cache: &ArcCache) -> Self {
        Self {
            content_type: arc_hashmap_to_hashmap(&cache.content_type),
            corosync_configuration: arc_hashmap_to_hashmap(&cache.corosync_configuration),
            active_alert: arc_hashmap_to_hashmap(&cache.active_alert),
            filesystem: arc_hashmap_to_hashmap(&cache.filesystem),
            group: arc_hashmap_to_hashmap(&cache.group),
            host: arc_hashmap_to_hashmap(&cache.host),
            lnet_configuration: arc_hashmap_to_hashmap(&cache.lnet_configuration),
            managed_target_mount: arc_hashmap_to_hashmap(&cache.managed_target_mount),
            ost_pool: arc_hashmap_to_hashmap(&cache.ost_pool),
            ost_pool_osts: arc_hashmap_to_hashmap(&cache.ost_pool_osts),
            pacemaker_configuration: arc_hashmap_to_hashmap(&cache.pacemaker_configuration),
            stratagem_config: arc_hashmap_to_hashmap(&cache.stratagem_config),
            target: arc_hashmap_to_hashmap(&cache.target),
            user: arc_hashmap_to_hashmap(&cache.user),
            user_group: arc_hashmap_to_hashmap(&cache.user_group),
            volume: arc_hashmap_to_hashmap(&cache.volume),
            volume_node: arc_hashmap_to_hashmap(&cache.volume_node),
        }
    }
}

#[allow(clippy::large_enum_variant)]
#[derive(serde::Serialize, serde::Deserialize, Debug, Clone)]
#[serde(tag = "tag", content = "payload")]
pub enum Record {
    ActiveAlert(Alert),
    ContentType(ContentTypeRecord),
    CorosyncConfiguration(CorosyncConfigurationRecord),
    Filesystem(Filesystem),
    Group(AuthGroupRecord),
    Host(Host),
    LnetConfiguration(LnetConfigurationRecord),
    ManagedTargetMount(ManagedTargetMountRecord),
    OstPool(OstPoolRecord),
    OstPoolOsts(OstPoolOstsRecord),
    PacemakerConfiguration(PacemakerConfigurationRecord),
    StratagemConfig(StratagemConfiguration),
    Target(Target<TargetConfParam>),
    User(AuthUserRecord),
    UserGroup(AuthUserGroupRecord),
    Volume(VolumeRecord),
    VolumeNode(VolumeNodeRecord),
}

#[derive(Debug, Clone)]
pub enum ArcRecord {
    ActiveAlert(Arc<Alert>),
    ContentType(Arc<ContentTypeRecord>),
    CorosyncConfiguration(Arc<CorosyncConfigurationRecord>),
    Filesystem(Arc<Filesystem>),
    Group(Arc<AuthGroupRecord>),
    Host(Arc<Host>),
    LnetConfiguration(Arc<LnetConfigurationRecord>),
    ManagedTargetMount(Arc<ManagedTargetMountRecord>),
    OstPool(Arc<OstPoolRecord>),
    OstPoolOsts(Arc<OstPoolOstsRecord>),
    PacemakerConfiguration(Arc<PacemakerConfigurationRecord>),
    StratagemConfig(Arc<StratagemConfiguration>),
    Target(Arc<Target<TargetConfParam>>),
    User(Arc<AuthUserRecord>),
    UserGroup(Arc<AuthUserGroupRecord>),
    Volume(Arc<VolumeRecord>),
    VolumeNode(Arc<VolumeNodeRecord>),
}

impl From<Record> for ArcRecord {
    fn from(record: Record) -> Self {
        match record {
            Record::ActiveAlert(x) => Self::ActiveAlert(Arc::new(x)),
            Record::ContentType(x) => Self::ContentType(Arc::new(x)),
            Record::CorosyncConfiguration(x) => Self::CorosyncConfiguration(Arc::new(x)),
            Record::Filesystem(x) => Self::Filesystem(Arc::new(x)),
            Record::Group(x) => Self::Group(Arc::new(x)),
            Record::Host(x) => Self::Host(Arc::new(x)),
            Record::LnetConfiguration(x) => Self::LnetConfiguration(Arc::new(x)),
            Record::ManagedTargetMount(x) => Self::ManagedTargetMount(Arc::new(x)),
            Record::OstPool(x) => Self::OstPool(Arc::new(x)),
            Record::OstPoolOsts(x) => Self::OstPoolOsts(Arc::new(x)),
            Record::PacemakerConfiguration(x) => Self::PacemakerConfiguration(Arc::new(x)),
            Record::StratagemConfig(x) => Self::StratagemConfig(Arc::new(x)),
            Record::Target(x) => Self::Target(Arc::new(x)),
            Record::User(x) => Self::User(Arc::new(x)),
            Record::UserGroup(x) => Self::UserGroup(Arc::new(x)),
            Record::Volume(x) => Self::Volume(Arc::new(x)),
            Record::VolumeNode(x) => Self::VolumeNode(Arc::new(x)),
        }
    }
}

#[derive(Clone, Copy, Debug, Hash, PartialEq, Eq, serde::Deserialize, serde::Serialize)]
#[serde(tag = "tag", content = "payload")]
pub enum RecordId {
    ActiveAlert(u32),
    ContentType(u32),
    CorosyncConfiguration(u32),
    Filesystem(u32),
    Group(u32),
    Host(u32),
    LnetConfiguration(u32),
    ManagedTargetMount(u32),
    OstPool(u32),
    OstPoolOsts(u32),
    PacemakerConfiguration(u32),
    StratagemConfig(u32),
    Target(u32),
    User(u32),
    UserGroup(u32),
    Volume(u32),
    VolumeNode(u32),
}

impl Deref for RecordId {
    type Target = u32;

    fn deref(&self) -> &u32 {
        match self {
            Self::ActiveAlert(x)
            | Self::ContentType(x)
            | Self::CorosyncConfiguration(x)
            | Self::Filesystem(x)
            | Self::Group(x)
            | Self::Host(x)
            | Self::ManagedTargetMount(x)
            | Self::OstPool(x)
            | Self::OstPoolOsts(x)
            | Self::PacemakerConfiguration(x)
            | Self::StratagemConfig(x)
            | Self::Target(x)
            | Self::User(x)
            | Self::UserGroup(x)
            | Self::Volume(x)
            | Self::VolumeNode(x)
            | Self::LnetConfiguration(x) => x,
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
    Locks(Locks),
    Records(Cache),
    RecordChange(RecordChange),
}

#[cfg(test)]
mod tests {
    use crate::{
        db::{OstPoolOstsRecord, OstPoolRecord},
        warp_drive::{ArcCache, ArcValuesExt, Cache},
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
            managedost_id: 1,
        });
        let rec2 = Arc::new(OstPoolOstsRecord {
            id: 2,
            ostpool_id: 2,
            managedost_id: 2,
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
                not_deleted: Some(true),
                content_type_id: Some(41),
            },
        );
        cache.ost_pool_osts.insert(
            18,
            OstPoolOstsRecord {
                id: 18,
                ostpool_id: 18,
                managedost_id: 13,
            },
        );
        cache.ost_pool_osts.insert(
            19,
            OstPoolOstsRecord {
                id: 19,
                ostpool_id: 18,
                managedost_id: 14,
            },
        );
        cache
    }
}
