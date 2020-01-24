    use crate::{
        db::{
            Id, LnetConfigurationRecord, ManagedTargetMountRecord, OstPoolOstsRecord,
            OstPoolRecord, StratagemConfiguration, VolumeNodeRecord,
        },
        Alert, Filesystem, Host, LockChange, Target, TargetConfParam, Volume,
    };
    use im::{HashMap, HashSet};
    use std::ops::Deref;
    use std::sync::Arc;

    fn hashmap_to_arc_hashmap<K, V>(hm: &HashMap<K, V>) -> HashMap<K, Arc<V>>
        where
            K: std::hash::Hash + Eq + Copy,
            V: Clone,
    {
        hm.iter().map(|(k, v)| (*k, Arc::new(v.clone()))).collect()
    }

    fn arc_hashmap_to_hashmap<K, V>(hm: &HashMap<K, Arc<V>>) -> HashMap<K, V>
        where
            K: std::hash::Hash + Eq + Copy,
            V: Clone,
    {
        hm.iter().map(|(k, v)| (*k, (**v).clone())).collect()
    }

    /// The current state of locks based on data from the locks queue
    pub type Locks = HashMap<String, HashSet<LockChange>>;

    /// Do not forget to keep [`Cache`](iml_wire_types::warp_drive::ArcCache) in sync
    #[derive(serde::Serialize, serde::Deserialize, Default, PartialEq, Clone, Debug)]
    pub struct FlatCache {
        pub active_alert: HashMap<u32, Alert>,
        pub filesystem: HashMap<u32, Filesystem>,
        pub host: HashMap<u32, Host>,
        pub lnet_configuration: HashMap<u32, LnetConfigurationRecord>,
        pub managed_target_mount: HashMap<u32, ManagedTargetMountRecord>,
        pub ost_pool: HashMap<u32, OstPoolRecord>,
        pub ost_pool_osts: HashMap<u32, OstPoolOstsRecord>,
        pub stratagem_config: HashMap<u32, StratagemConfiguration>,
        pub target: HashMap<u32, Target<TargetConfParam>>,
        pub volume: HashMap<u32, Volume>,
        pub volume_node: HashMap<u32, VolumeNodeRecord>,
    }

    /// Do not forget to keep [`FlatCache`](iml_wire_types::warp_drive::Cache) in sync
    #[derive(serde::Serialize, serde::Deserialize, Default, PartialEq, Clone, Debug)]
    pub struct Cache {
        pub active_alert: HashMap<u32, Arc<Alert>>,
        pub filesystem: HashMap<u32, Arc<Filesystem>>,
        pub host: HashMap<u32, Arc<Host>>,
        pub lnet_configuration: HashMap<u32, Arc<LnetConfigurationRecord>>,
        pub managed_target_mount: HashMap<u32, Arc<ManagedTargetMountRecord>>,
        pub ost_pool: HashMap<u32, Arc<OstPoolRecord>>,
        pub ost_pool_osts: HashMap<u32, Arc<OstPoolOstsRecord>>,
        pub stratagem_config: HashMap<u32, Arc<StratagemConfiguration>>,
        pub target: HashMap<u32, Arc<Target<TargetConfParam>>>,
        pub volume: HashMap<u32, Arc<Volume>>,
        pub volume_node: HashMap<u32, Arc<VolumeNodeRecord>>,
    }

    impl FlatCache {
        /// Removes the record from the cache
        pub fn remove_record(&mut self, x: &RecordId) -> bool {
            match x {
                RecordId::ActiveAlert(id) => self.active_alert.remove(id).is_some(),
                RecordId::Filesystem(id) => self.filesystem.remove(id).is_some(),
                RecordId::Host(id) => self.host.remove(id).is_some(),
                RecordId::LnetConfiguration(id) => self.lnet_configuration.remove(id).is_some(),
                RecordId::ManagedTargetMount(id) => self.managed_target_mount.remove(id).is_some(),
                RecordId::OstPool(id) => self.ost_pool.remove(id).is_some(),
                RecordId::OstPoolOsts(id) => self.ost_pool_osts.remove(id).is_some(),
                RecordId::StratagemConfig(id) => self.stratagem_config.remove(id).is_some(),
                RecordId::Target(id) => self.target.remove(id).is_some(),
                RecordId::Volume(id) => self.volume.remove(id).is_some(),
                RecordId::VolumeNode(id) => self.volume_node.remove(id).is_some(),
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
                Record::OstPool(x) => {
                    self.ost_pool.insert(x.id(), x);
                }
                Record::OstPoolOsts(x) => {
                    self.ost_pool_osts.insert(x.id(), x);
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

    impl Cache {
        /// Removes the record from the cache
        pub fn remove_record(&mut self, x: &RecordId) -> bool {
            match x {
                RecordId::ActiveAlert(id) => self.active_alert.remove(id).is_some(),
                RecordId::Filesystem(id) => self.filesystem.remove(id).is_some(),
                RecordId::Host(id) => self.host.remove(id).is_some(),
                RecordId::LnetConfiguration(id) => self.lnet_configuration.remove(id).is_some(),
                RecordId::ManagedTargetMount(id) => self.managed_target_mount.remove(id).is_some(),
                RecordId::OstPool(id) => self.ost_pool.remove(id).is_some(),
                RecordId::OstPoolOsts(id) => self.ost_pool_osts.remove(id).is_some(),
                RecordId::StratagemConfig(id) => self.stratagem_config.remove(id).is_some(),
                RecordId::Target(id) => self.target.remove(id).is_some(),
                RecordId::Volume(id) => self.volume.remove(id).is_some(),
                RecordId::VolumeNode(id) => self.volume_node.remove(id).is_some(),
            }
        }
        /// Inserts the record into the cache
        pub fn insert_record(&mut self, x: Record) {
            match x {
                Record::ActiveAlert(x) => {
                    self.active_alert.insert(x.id, Arc::new(x));
                }
                Record::Filesystem(x) => {
                    self.filesystem.insert(x.id, Arc::new(x));
                }
                Record::Host(x) => {
                    self.host.insert(x.id, Arc::new(x));
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
                Record::StratagemConfig(x) => {
                    self.stratagem_config.insert(x.id(), Arc::new(x));
                }
                Record::Target(x) => {
                    self.target.insert(x.id, Arc::new(x));
                }
                Record::Volume(x) => {
                    self.volume.insert(x.id, Arc::new(x));
                }
                Record::VolumeNode(x) => {
                    self.volume_node.insert(x.id(), Arc::new(x));
                }
            }
        }
    }

    impl<'a> From<&'a FlatCache> for Cache {
        fn from(cache: &FlatCache) -> Self {
            Self {
                active_alert: hashmap_to_arc_hashmap(&cache.active_alert),
                filesystem: hashmap_to_arc_hashmap(&cache.filesystem),
                host: hashmap_to_arc_hashmap(&cache.host),
                lnet_configuration: hashmap_to_arc_hashmap(&cache.lnet_configuration),
                managed_target_mount: hashmap_to_arc_hashmap(&cache.managed_target_mount),
                ost_pool: hashmap_to_arc_hashmap(&cache.ost_pool),
                ost_pool_osts: hashmap_to_arc_hashmap(&cache.ost_pool_osts),
                stratagem_config: hashmap_to_arc_hashmap(&cache.stratagem_config),
                target: hashmap_to_arc_hashmap(&cache.target),
                volume: hashmap_to_arc_hashmap(&cache.volume),
                volume_node: hashmap_to_arc_hashmap(&cache.volume_node),
            }
        }
    }

    impl<'a> From<&'a Cache> for FlatCache {
        fn from(cache: &Cache) -> Self {
            Self {
                active_alert: arc_hashmap_to_hashmap(&cache.active_alert),
                filesystem: arc_hashmap_to_hashmap(&cache.filesystem),
                host: arc_hashmap_to_hashmap(&cache.host),
                lnet_configuration: arc_hashmap_to_hashmap(&cache.lnet_configuration),
                managed_target_mount: arc_hashmap_to_hashmap(&cache.managed_target_mount),
                ost_pool: arc_hashmap_to_hashmap(&cache.ost_pool),
                ost_pool_osts: arc_hashmap_to_hashmap(&cache.ost_pool_osts),
                stratagem_config: arc_hashmap_to_hashmap(&cache.stratagem_config),
                target: arc_hashmap_to_hashmap(&cache.target),
                volume: arc_hashmap_to_hashmap(&cache.volume),
                volume_node: arc_hashmap_to_hashmap(&cache.volume_node),
            }
        }
    }

    #[derive(serde::Serialize, serde::Deserialize, Debug, Clone)]
    #[serde(tag = "tag", content = "payload")]
    pub enum Record {
        ActiveAlert(Alert),
        Filesystem(Filesystem),
        Host(Host),
        ManagedTargetMount(ManagedTargetMountRecord),
        OstPool(OstPoolRecord),
        OstPoolOsts(OstPoolOstsRecord),
        StratagemConfig(StratagemConfiguration),
        Target(Target<TargetConfParam>),
        Volume(Volume),
        VolumeNode(VolumeNodeRecord),
        LnetConfiguration(LnetConfigurationRecord),
    }

    #[derive(Clone, Copy, Debug, Hash, PartialEq, Eq, serde::Deserialize, serde::Serialize)]
    #[serde(tag = "tag", content = "payload")]
    pub enum RecordId {
        ActiveAlert(u32),
        Filesystem(u32),
        Host(u32),
        ManagedTargetMount(u32),
        OstPool(u32),
        OstPoolOsts(u32),
        StratagemConfig(u32),
        Target(u32),
        Volume(u32),
        VolumeNode(u32),
        LnetConfiguration(u32),
    }

    impl Deref for RecordId {
        type Target = u32;

        fn deref(&self) -> &u32 {
            match self {
                Self::ActiveAlert(x)
                | Self::Filesystem(x)
                | Self::Host(x)
                | Self::ManagedTargetMount(x)
                | Self::OstPool(x)
                | Self::OstPoolOsts(x)
                | Self::StratagemConfig(x)
                | Self::Target(x)
                | Self::Volume(x)
                | Self::VolumeNode(x)
                | Self::LnetConfiguration(x) => x,
            }
        }
    }

    #[derive(Debug, serde::Serialize, serde::Deserialize, Clone)]
    #[serde(tag = "tag", content = "payload")]
    pub enum RecordChange {
        Update(Record),
        Delete(RecordId),
    }

    /// Message variants.
    #[derive(serde::Serialize, serde::Deserialize, Clone, Debug)]
    #[serde(tag = "tag", content = "payload")]
    pub enum Message {
        Locks(Locks),
        Records(Cache),
        RecordChange(RecordChange),
    }
