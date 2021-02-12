// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub mod error;
pub mod filesystems;

use device_types::{
    devices::{Device, DeviceId},
    mount::Mount,
};
use emf_change::*;
use emf_tracing::tracing;
use emf_wire_types::{Fqdn, FsType};
pub use error::EmfDeviceError;
use futures::{future::try_join_all, lock::Mutex, TryStreamExt};
use im::HashSet;
use sqlx::postgres::PgPool;
use std::{
    collections::{BTreeMap, BTreeSet, HashMap},
    sync::Arc,
};

pub type Cache = Arc<Mutex<HashMap<Fqdn, Device>>>;
pub type TargetFsRecord = HashMap<String, Vec<(Fqdn, String)>>;

#[derive(serde::Serialize, serde::Deserialize)]
struct FsRecord {
    host: String,
    target: String,
    fs: Option<String>,
    mgs_fs: Option<String>,
}

/// Given a db pool, create a new cache and fill it with initial data.
/// This will start the device tree with the previous items it left off with.
pub async fn create_cache(pool: &PgPool) -> Result<Cache, EmfDeviceError> {
    let data = sqlx::query!("select * from device")
        .fetch_all(pool)
        .await?
        .into_iter()
        .map(|x| -> Result<(Fqdn, Device), EmfDeviceError> {
            let d = serde_json::from_value(x.devices)?;

            Ok((Fqdn(x.fqdn), d))
        })
        .collect::<Result<_, _>>()?;

    Ok(Arc::new(Mutex::new(data)))
}

pub async fn create_target_cache(pool: &PgPool) -> Result<Vec<Target>, EmfDeviceError> {
    let xs: Vec<Target> = sqlx::query_as!(Target, r#"SELECT state, name, active_host_id, host_ids, filesystems, uuid, mount_path, dev_path, fs_type AS "fs_type: FsType" FROM target"#)
        .fetch(pool)
        .try_collect()
        .await?;

    Ok(xs)
}

pub async fn update_devices(
    pool: &PgPool,
    host: &Fqdn,
    devices: &Device,
) -> Result<(), EmfDeviceError> {
    tracing::info!("Inserting devices from host '{}'", host);
    tracing::debug!("Inserting {:?}", devices);

    sqlx::query!(
        r#"
        INSERT INTO device
        (fqdn, devices)
        VALUES ($1, $2)
        ON CONFLICT (fqdn) DO UPDATE
        SET devices = EXCLUDED.devices
    "#,
        host.to_string(),
        serde_json::to_value(devices)?
    )
    .execute(pool)
    .await?;

    Ok(())
}

pub async fn update_client_mounts(
    pool: &PgPool,
    host: &Fqdn,
    mounts: &HashSet<Mount>,
) -> Result<(), EmfDeviceError> {
    let host_id: Option<i32> =
        sqlx::query!("select id from host where fqdn = $1", host.to_string())
            .fetch_optional(pool)
            .await?
            .map(|x| x.id);

    let host_id = match host_id {
        Some(id) => id,
        None => {
            tracing::warn!("Host '{}' is unknown", host);

            return Ok(());
        }
    };

    let mount_map = mounts
        .into_iter()
        .filter(|m| m.fs_type.0 == "lustre")
        .filter(|m| m.opts.0.split(',').find(|x| x == &"ro").is_none())
        .filter_map(|m| {
            m.source
                .0
                .to_str()
                .and_then(|p| p.splitn(2, ":/").nth(1))
                .map(|fs| (fs.to_string(), m.target.0.to_string_lossy().to_string()))
        })
        .fold(HashMap::new(), |mut acc, (fs_name, mountpoint)| {
            let mountpoints = acc.entry(fs_name).or_insert_with(BTreeSet::new);

            mountpoints.insert(mountpoint);

            acc
        });

    tracing::debug!("Client mounts at {}({}): {:?}", host, host_id, &mount_map);

    let xs = mount_map
        .into_iter()
        .map(|(fs_name, mountpoints)| async move {
            let mountpoints: Vec<String> = mountpoints.into_iter().collect();

            let x = sqlx::query!(
                r#"
        INSERT INTO lustreclientmount
        (host_id, filesystem, mountpoints, state, state_modified_at)
        VALUES ($1, $2, $3, 'mounted', now())
        ON CONFLICT (host_id, filesystem) DO UPDATE
        SET 
            mountpoints = excluded.mountpoints,
            state = excluded.state,
            state_modified_at = excluded.state_modified_at
        RETURNING id
    "#,
                host_id,
                &fs_name,
                &mountpoints
            )
            .fetch_all(pool)
            .await?;

            Ok::<_, EmfDeviceError>(x)
        });

    let xs: Vec<_> = try_join_all(xs)
        .await?
        .into_iter()
        .flatten()
        .map(|x| x.id)
        .collect();

    let updated = sqlx::query!(
        r#"
            UPDATE lustreclientmount
            SET 
                mountpoints = array[]::text[],
                state = 'unmounted',
                state_modified_at = now()
            WHERE host_id = $1
            AND id != ALL($2)
        "#,
        host_id,
        &xs
    )
    .execute(pool)
    .await?;

    tracing::debug!("Updated client mounts: {:?}", updated);

    Ok(())
}

#[derive(Debug, serde::Serialize)]
pub struct DeviceMap(BTreeMap<DeviceId, BTreeSet<Vec<DeviceId>>>);

impl DeviceMap {
    fn get_shared_parent(&self, id: &DeviceId) -> Option<(&DeviceId, &BTreeSet<Vec<DeviceId>>)> {
        let item = self.0.get(id)?;

        if id.0.starts_with("lv_") {
            let vg = item.iter().find_map(|xs| {
                let x = xs.last()?;

                if x.0.starts_with("vg_") {
                    Some(x)
                } else {
                    None
                }
            })?;

            Some((vg, self.0.get(&vg)?))
        } else {
            None
        }
    }
}

#[derive(Debug, serde::Serialize)]
pub struct DeviceIndex<'a>(HashMap<&'a Fqdn, DeviceMap>);

pub fn build_device_index<'a>(x: &'a HashMap<Fqdn, Device>) -> DeviceIndex<'a> {
    let mut device_index: HashMap<&Fqdn, DeviceMap> = x
        .iter()
        .map(|(fqdn, device)| {
            let mut map = DeviceMap(BTreeMap::new());

            build_device_map(device, &mut map, &[]);

            (fqdn, map)
        })
        .collect();

    let xs = device_index.iter().fold(vec![], |mut acc, (fqdn, map)| {
        let others = device_index.iter().filter(|(x, _)| &fqdn != x).collect();

        acc.extend(add_shared_storage(map, others));

        acc
    });

    for (fqdn, device_id, paths) in xs {
        let map = match device_index.get_mut(&fqdn) {
            Some(x) => x,
            None => continue,
        };

        map.0.insert(device_id.clone(), paths.clone());
    }

    DeviceIndex(device_index)
}

fn add_shared_storage<'a>(
    map: &'a DeviceMap,
    other: HashMap<&'a &Fqdn, &DeviceMap>,
) -> Vec<(Fqdn, DeviceId, BTreeSet<Vec<DeviceId>>)> {
    let xs: Vec<_> = map
        .0
        .iter()
        .filter(|(device_id, _)| {
            device_id.0.starts_with("lv_") || device_id.0.starts_with("mdraid_")
        })
        .collect();

    let mut matches = vec![];

    for (existing_id, parents) in xs {
        if existing_id.0.starts_with("lv_") {
            let shared = map.get_shared_parent(existing_id);

            if let Some((shared_id, shared_parents)) = shared {
                let parent_ids = shared_parents
                    .iter()
                    .filter_map(|xs| xs.last())
                    .collect::<Vec<_>>();

                matches = other
                    .iter()
                    .filter(|(_, map)| parent_ids.iter().all(|p| map.0.get(p).is_some()))
                    .map(|(fqdn, _)| {
                        vec![
                            ((**fqdn).clone(), shared_id.clone(), shared_parents.clone()),
                            ((**fqdn).clone(), existing_id.clone(), parents.clone()),
                        ]
                    })
                    .flatten()
                    .chain(matches)
                    .collect();
            }
        } else {
            let parent_ids = parents
                .iter()
                .filter_map(|xs| xs.last())
                .collect::<Vec<_>>();

            matches = other
                .iter()
                .filter(|(_, map)| parent_ids.iter().all(|p| map.0.get(p).is_some()))
                .map(|(fqdn, _)| ((**fqdn).clone(), existing_id.clone(), parents.clone()))
                .chain(matches)
                .collect();
        }
    }

    matches
}

fn build_device_map(device: &Device, map: &mut DeviceMap, path: &[DeviceId]) {
    let id = match device.get_id() {
        Some(x) => x,
        None => return,
    };

    let paths = map.0.entry(id.clone()).or_insert_with(BTreeSet::new);

    paths.insert(path.to_vec());

    let parent_path = [path.to_vec(), vec![id]].concat();

    let children = match device.children() {
        Some(x) => x,
        None => return,
    };

    children
        .iter()
        .for_each(|d| build_device_map(d, map, &parent_path));
}

pub fn find_targets<'a>(
    x: &'a HashMap<Fqdn, Device>,
    mounts: &HashMap<Fqdn, HashSet<Mount>>,
    host_map: &HashMap<Fqdn, i32>,
    device_index: &DeviceIndex<'a>,
    mgs_fs_cache: &HashMap<Fqdn, Vec<String>>,
) -> Vec<Target> {
    let xs: Vec<_> = mounts
        .iter()
        .map(|(k, xs)| xs.into_iter().map(move |x| (k, x)))
        .flatten()
        .filter(|(_, x)| x.fs_type.0 == "lustre")
        .filter(|(_, x)| !x.source.0.to_string_lossy().contains('@'))
        .filter_map(|(fqdn, x)| {
            let opts: Vec<_> = x.opts.0.split(',').collect();

            let is_mgs = opts.contains(&"mgs");

            let svname = opts.into_iter().find(|x| x.starts_with("svname="))?;
            let svname = svname.split('=').nth(1)?;

            let osd = x.opts.0.split(',').find(|x| x.starts_with("osd="))?;
            let osd = osd.split('=').nth(1)?;

            let mut xs = vec![(fqdn, &x.target, &x.source, svname, osd)];

            if is_mgs {
                xs.push((fqdn, &x.target, &x.source, "MGS", osd));
            }

            Some(xs)
        })
        .flatten()
        .collect();

    let xs: Vec<_> = xs
        .into_iter()
        .filter_map(|(fqdn, mntpnt, dev, target, osd)| {
            let dev_tree = x.get(&fqdn)?;

            let device = dev_tree.find_device_by_devpath(dev)?;

            let dev_id = device.get_id()?;

            let fs_uuid = device.get_fs_uuid()?;

            Some((fqdn, mntpnt, dev_id, dev, fs_uuid, target, osd))
        })
        .collect();

    let xs: Vec<_> = xs
        .into_iter()
        .filter_map(|(fqdn, mntpnt, dev_id, dev_path, fs_uuid, target, osd)| {
            let ys: Vec<_> = device_index
                .0
                .iter()
                .filter(|(k, _)| *k != &fqdn)
                .filter_map(|(k, x)| {
                    tracing::debug!("Searching for device {:?} on {}", dev_id, &k);
                    x.0.get(&dev_id)?;

                    tracing::debug!("found device on {}!", &k);
                    let host_id = host_map.get(&k)?;

                    Some(*host_id)
                })
                .collect();

            tracing::debug!("ys: {:?}", ys);

            let host_id = host_map.get(&fqdn)?;
            tracing::debug!("host id: {:?}", host_id);

            Some((
                fqdn,
                host_id,
                [vec![*host_id], ys].concat(),
                mntpnt,
                fs_uuid,
                dev_path,
                target,
                osd,
            ))
        })
        .collect();

    xs.into_iter()
        .map(
            |(fqdn, host_id, ids, mntpnt, fs_uuid, dev_path, target, osd)| {
                let filesystems = if target == "MGS" {
                    mgs_fs_cache.get(&fqdn).cloned().unwrap_or_default()
                } else {
                    target
                        .rsplitn(2, '-')
                        .nth(1)
                        .map(String::from)
                        .map(|x| vec![x])
                        .unwrap_or_default()
                };

                Target {
                    state: "mounted".into(),
                    active_host_id: Some(*host_id),
                    host_ids: ids,
                    dev_path: Some(dev_path.0.to_string_lossy().to_string()),
                    filesystems,
                    name: target.into(),
                    uuid: fs_uuid.into(),
                    mount_path: Some(mntpnt.0.to_string_lossy().to_string()),
                    fs_type: match osd {
                        osd if osd.contains("zfs") => Some(FsType::Zfs),
                        osd if osd.contains("ldiskfs") => Some(FsType::Ldiskfs),
                        _ => None,
                    },
                }
            },
        )
        .fold(HashMap::new(), |mut acc: HashMap<String, Target>, x| {
            // We may have multiple incoming mounts for the same uuid.
            // This could happen when a target moves quickly but not all agents have reported new
            // data yet. Handle this case by indexing by name:uuid and only overwritting
            // if the current target has no associated filesystems.

            let key = format!("{}:{}", x.name, x.uuid);
            match acc.get(&key) {
                Some(y) if y.filesystems.is_empty() => {
                    acc.insert(key, x);
                }
                None => {
                    acc.insert(key, x);
                }
                Some(y) => {
                    tracing::info!("Skipping insert for {:?}, because we have {:?}", x, y);
                }
            };

            acc
        })
        .into_iter()
        .map(|(_, x)| x)
        .collect::<Vec<_>>()
}

#[derive(Debug, Eq, PartialEq, Ord, PartialOrd, Clone)]
pub struct Target {
    pub state: String,
    pub name: String,
    pub dev_path: Option<String>,
    pub active_host_id: Option<i32>,
    pub host_ids: Vec<i32>,
    pub filesystems: Vec<String>,
    pub uuid: String,
    pub mount_path: Option<String>,
    pub fs_type: Option<FsType>,
}

impl Identifiable for Target {
    type Id = String;

    fn id(&self) -> Self::Id {
        self.uuid.clone()
    }
}

impl Target {
    pub fn set_unmounted(&mut self) {
        self.state = "unmounted".into();
        self.active_host_id = None;
    }
}

pub fn build_updates(x: Changes<'_, Target>) -> Vec<Target> {
    match x {
        (Some(Upserts(up)), Some(Deletions(del))) => del
            .into_iter()
            .cloned()
            .map(|mut t| {
                t.set_unmounted();

                t
            })
            .chain(up.into_iter().cloned())
            .collect(),
        (Some(Upserts(xs)), None) => xs.into_iter().cloned().collect(),
        (None, Some(Deletions(xs))) => xs
            .into_iter()
            .cloned()
            .map(|mut t| {
                t.set_unmounted();

                t
            })
            .collect(),
        (None, None) => vec![],
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use device_types::devices::Device;
    use insta::assert_json_snapshot;

    #[test]
    fn test_index() {
        let cluster: HashMap<Fqdn, Device> =
            serde_json::from_slice(include_bytes!("../fixtures/devtrees.json")).unwrap();
        let index = build_device_index(&cluster);

        insta::with_settings!({sort_maps => true}, {
            assert_json_snapshot!(index);
        });
    }

    #[test]
    fn test_upserts_only() {
        let ups = vec![
            Target {
                state: "mounted".into(),
                name: "mdt1".into(),
                dev_path: None,
                active_host_id: Some(1),
                host_ids: vec![2],
                filesystems: vec!["fs1".to_string()],
                uuid: "123456".into(),
                mount_path: Some("/mnt/mdt1".into()),
                fs_type: Some(FsType::Ldiskfs),
            },
            Target {
                state: "mounted".into(),
                name: "ost1".into(),
                dev_path: Some("/dev/mapper/mpathz".to_string()),
                active_host_id: Some(3),
                host_ids: vec![4],
                filesystems: vec!["fs1".to_string()],
                uuid: "567890".into(),
                mount_path: Some("/mnt/ost1".into()),
                fs_type: Some(FsType::Ldiskfs),
            },
        ];

        let upserts = Upserts(ups.iter().collect());

        let xs = build_updates((Some(upserts), None));

        insta::assert_debug_snapshot!(xs);
    }

    #[test]
    fn test_upserts_and_deletions() {
        let t = Target {
            state: "mounted".into(),
            name: "mdt1".into(),
            dev_path: None,
            active_host_id: Some(1),
            host_ids: vec![2],
            filesystems: vec!["fs1".to_string()],
            uuid: "123456".into(),
            mount_path: Some("/mnt/mdt1".into()),
            fs_type: Some(FsType::Ldiskfs),
        };

        let deletions = Deletions(vec![&t]);

        let ups = vec![
            Target {
                state: "mounted".into(),
                name: "mdt2".into(),
                dev_path: None,
                active_host_id: Some(2),
                host_ids: vec![1],
                filesystems: vec!["fs1".to_string()],
                uuid: "654321".into(),
                mount_path: Some("/mnt/mdt2".into()),
                fs_type: Some(FsType::Ldiskfs),
            },
            Target {
                state: "mounted".into(),
                name: "ost1".into(),
                dev_path: None,
                active_host_id: Some(3),
                host_ids: vec![4],
                filesystems: vec!["fs1".to_string()],
                uuid: "567890".into(),
                mount_path: Some("/mnt/ost1".into()),
                fs_type: Some(FsType::Ldiskfs),
            },
        ];

        let upserts = Upserts(ups.iter().collect());

        let xs = build_updates((Some(upserts), Some(deletions)));

        insta::assert_debug_snapshot!(xs);
    }

    #[test]
    fn test_deletions_only() {
        let t = Target {
            state: "mounted".into(),
            name: "mdt1".into(),
            dev_path: None,
            active_host_id: Some(1),
            host_ids: vec![2],
            filesystems: vec!["fs1".into()],
            uuid: "123456".into(),
            mount_path: Some("/mnt/mdt1".into()),
            fs_type: Some(FsType::Ldiskfs),
        };

        let deletions = Deletions(vec![&t]);

        let xs = build_updates((None, Some(deletions)));

        insta::assert_debug_snapshot!(xs);
    }

    #[test]
    fn test_no_upserts_or_deletions() {
        let xs = build_updates((None, None));

        assert_eq!(xs, vec![]);
    }
}
