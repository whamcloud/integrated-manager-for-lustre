// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub mod error;
pub mod linux_plugin_transforms;

pub use error::ImlDeviceError;

use device_types::{
    devices::{Device, DeviceId},
    mount::Mount,
};
use futures::{future::try_join_all, lock::Mutex};
use im::HashSet;
use iml_change::*;
use iml_postgres::sqlx::{self, PgPool};
use iml_tracing::tracing;
use iml_wire_types::Fqdn;
use influx_db_client::{keys::Node, Client, Precision};
use std::{
    collections::{BTreeMap, BTreeSet, HashMap},
    sync::Arc,
};

pub type Cache = Arc<Mutex<HashMap<Fqdn, Device>>>;
pub type TargetFsRecord = HashMap<String, Vec<(Fqdn, String)>>;

/// Given a db pool, create a new cache and fill it with initial data.
/// This will start the device tree with the previous items it left off with.
pub async fn create_cache(pool: &PgPool) -> Result<Cache, ImlDeviceError> {
    let data = sqlx::query!("select * from chroma_core_device")
        .fetch_all(pool)
        .await?
        .into_iter()
        .map(|x| -> Result<(Fqdn, Device), ImlDeviceError> {
            let d = serde_json::from_value(x.devices)?;

            Ok((Fqdn(x.fqdn), d))
        })
        .collect::<Result<_, _>>()?;

    Ok(Arc::new(Mutex::new(data)))
}

pub async fn create_target_cache(pool: &PgPool) -> Result<Vec<Target>, ImlDeviceError> {
    let xs: Vec<Target> = sqlx::query_as!(Target, "select * from targets")
        .fetch_all(pool)
        .await?;

    Ok(xs)
}

pub async fn update_devices(
    pool: &PgPool,
    host: &Fqdn,
    devices: &Device,
) -> Result<(), ImlDeviceError> {
    tracing::info!("Inserting devices from host '{}'", host);
    tracing::debug!("Inserting {:?}", devices);

    sqlx::query!(
        r#"
        INSERT INTO chroma_core_device
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

pub async fn client_mount_content_id(pool: &PgPool) -> Result<Option<i32>, ImlDeviceError> {
    let id = sqlx::query!("select id from django_content_type where model = 'lustreclientmount'")
        .fetch_optional(pool)
        .await?
        .map(|x| x.id);

    Ok(id)
}

pub async fn update_client_mounts(
    pool: &PgPool,
    ct_id: Option<i32>,
    host: &Fqdn,
    mounts: &HashSet<Mount>,
) -> Result<(), ImlDeviceError> {
    let host_id: Option<i32> = sqlx::query!(
        "select id from chroma_core_managedhost where fqdn = $1 and not_deleted = 't'",
        host.to_string()
    )
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

    let xs = mount_map.into_iter().map(|(fs_name, mountpoints)| async move {
        let mountpoints:Vec<String> = mountpoints.into_iter().collect();

        let x = sqlx::query!(
            r#"
        INSERT INTO chroma_core_lustreclientmount
        (host_id, filesystem, mountpoints, state, state_modified_at, immutable_state, not_deleted, content_type_id)
        VALUES ($1, $2, $3, 'mounted', now(), 'f', 't', $4)
        ON CONFLICT (host_id, filesystem, not_deleted) DO UPDATE
        SET 
            mountpoints = excluded.mountpoints,
            state = excluded.state,
            state_modified_at = excluded.state_modified_at
        RETURNING id
    "#,
            host_id,
            &fs_name,
            &mountpoints,
            ct_id,
        ).fetch_all(pool).await?;

        Ok::<_, ImlDeviceError>(x)
    });

    let xs: Vec<_> = try_join_all(xs)
        .await?
        .into_iter()
        .flatten()
        .map(|x| x.id)
        .collect();

    let updated = sqlx::query!(
        r#"
            UPDATE chroma_core_lustreclientmount
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
        } else if id.0.starts_with("dataset_") {
            let zpool = item.iter().find_map(|xs| {
                let x = xs.last()?;

                if x.0.starts_with("zpool_") {
                    Some(x)
                } else {
                    None
                }
            })?;

            Some((zpool, self.0.get(&zpool)?))
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
            device_id.0.starts_with("lv_")
                || device_id.0.starts_with("dataset_")
                || device_id.0.starts_with("mdraid_")
        })
        .collect();

    let mut matches = vec![];

    for (existing_id, parents) in xs {
        if existing_id.0.starts_with("lv_") || existing_id.0.starts_with("dataset_") {
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
    target_to_fs_map: &TargetFsRecord,
) -> Vec<Target> {
    let xs: Vec<_> = mounts
        .iter()
        .map(|(k, xs)| xs.into_iter().map(move |x| (k, x)))
        .flatten()
        .filter(|(_, x)| x.fs_type.0 == "lustre")
        .filter(|(_, x)| !x.source.0.to_string_lossy().contains('@'))
        .filter_map(|(fqdn, x)| {
            let s = x.opts.0.split(',').find(|x| x.starts_with("svname="))?;

            let s = s.split('=').nth(1)?;

            Some((fqdn, &x.target, &x.source, s))
        })
        .collect();

    let xs: Vec<_> = xs
        .into_iter()
        .filter_map(|(fqdn, mntpnt, dev, target)| {
            let dev_tree = x.get(&fqdn)?;

            let device = dev_tree.find_device_by_devpath(dev)?;

            let dev_id = device.get_id()?;

            let fs_uuid = device.get_fs_uuid()?;

            Some((fqdn, mntpnt, dev_id, fs_uuid, target))
        })
        .collect();

    let xs: Vec<_> = xs
        .into_iter()
        .filter_map(|(fqdn, mntpnt, dev_id, fs_uuid, target)| {
            let ys: Vec<_> = device_index
                .0
                .iter()
                .filter(|(k, _)| *k != &fqdn)
                .filter_map(|(k, x)| {
                    tracing::debug!("Searching for device {:?} on {}", &x, &k);
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
                host_id,
                [vec![*host_id], ys].concat(),
                mntpnt,
                fs_uuid,
                target,
            ))
        })
        .collect();

    xs.into_iter()
        .map(|(fqdn, ids, mntpnt, fs_uuid, target)| Target {
            state: "mounted".into(),
            active_host_id: Some(*fqdn),
            host_ids: ids,
            filesystems: target_to_fs_map
                .get(target)
                .map(|xs| {
                    xs.iter()
                        .filter(|(host, _)| {
                            host_map
                                .get(host)
                                .expect(format!("Couldn't get host {}", host.0).as_str())
                                == fqdn
                        })
                        .map(|(_, fs)| fs.clone())
                        .collect::<Vec<String>>()
                })
                .unwrap_or(vec![]),
            name: target.into(),
            uuid: fs_uuid.into(),
            mount_path: Some(mntpnt.0.to_string_lossy().to_string()),
        })
        .collect()
}

#[derive(Debug, Eq, PartialEq, Ord, PartialOrd, Clone)]
pub struct Target {
    pub state: String,
    pub name: String,
    pub active_host_id: Option<i32>,
    pub host_ids: Vec<i32>,
    pub filesystems: Vec<String>,
    pub uuid: String,
    pub mount_path: Option<String>,
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
        self.mount_path = None;
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

fn parse_filesystem_data(query_result: Option<Vec<Node>>, tag: &str) -> TargetFsRecord {
    let target_to_fs = if let Some(nodes) = query_result {
        let items = nodes
            .into_iter()
            .filter_map(|x| x.series)
            .map(|xs| {
                xs.into_iter()
                    .map(|x| {
                        let columns = x.columns;
                        x.values
                            .into_iter()
                            .map(|v| {
                                columns
                                    .iter()
                                    .cloned()
                                    .zip(v.into_iter())
                                    .collect::<HashMap<String, serde_json::Value>>()
                            })
                            .collect::<Vec<HashMap<String, serde_json::Value>>>()
                    })
                    .flatten()
                    .map(|mut x| {
                        let filesystems: String = serde_json::from_value(
                            x.remove(tag).unwrap_or_else(|| serde_json::json!("")),
                        )
                        .unwrap_or_else(|_| panic!("Couldn't parse {} name.", tag));

                        let host: String = serde_json::from_value(
                            x.remove("host".into())
                                .unwrap_or_else(|| serde_json::json!("")),
                        )
                        .expect("Couldn't parse host.");

                        (
                            serde_json::from_value(
                                x.remove("target").unwrap_or_else(|| serde_json::json!("")),
                            )
                            .expect("Couldn't parse target."),
                            filesystems
                                .split(",")
                                .map(|x| (Fqdn(host.clone()), x.to_string()))
                                .collect(),
                        )
                    })
                    .collect::<Vec<(String, Vec<(Fqdn, String)>)>>()
            })
            .flatten()
            .collect::<Vec<(String, Vec<(Fqdn, String)>)>>();

        items.into_iter().fold(
            HashMap::new(),
            |mut acc: HashMap<String, Vec<(Fqdn, String)>>, xs| {
                let existing = acc.remove(xs.0.as_str());

                let x = if let Some(entry) = existing {
                    [&entry[..], &xs.1[..]].concat()
                } else {
                    xs.1
                };

                acc.insert(xs.0, x);

                acc
            },
        )
    } else {
        HashMap::new()
    };

    tracing::debug!("target_to_fs: {:?}", target_to_fs);

    target_to_fs
}

pub async fn get_target_filesystem_map(
    influx_client: &Client,
) -> Result<TargetFsRecord, ImlDeviceError> {
    let query_result: Option<Vec<Node>> = influx_client
        .query(
            "select host,target,fs,bytes_free from target group by target order by time desc limit 1;",
            Some(Precision::Nanoseconds),
        )
        .await?;

    Ok(parse_filesystem_data(query_result, "fs"))
}

pub async fn get_mgs_filesystem_map(
    influx_client: &Client,
) -> Result<TargetFsRecord, ImlDeviceError> {
    let query_result: Option<Vec<Node>> = influx_client
        .query(
            "select host,target,mgs_fs from target;",
            Some(Precision::Nanoseconds),
        )
        .await?;

    Ok(parse_filesystem_data(query_result, "mgs_fs"))
}

#[cfg(test)]
mod tests {
    use super::*;
    use device_types::devices::Device;
    use influx_db_client::keys::Series;
    use insta::assert_json_snapshot;
    use serde_json::{json, Map, Value};

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
                active_host_id: Some(1),
                host_ids: vec![2],
                filesystems: vec!["fs1".to_string()],
                uuid: "123456".into(),
                mount_path: Some("/mnt/mdt1".into()),
            },
            Target {
                state: "mounted".into(),
                name: "ost1".into(),
                active_host_id: Some(3),
                host_ids: vec![4],
                filesystems: vec!["fs1".to_string()],
                uuid: "567890".into(),
                mount_path: Some("/mnt/ost1".into()),
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
            active_host_id: Some(1),
            host_ids: vec![2],
            filesystems: vec!["fs1".to_string()],
            uuid: "123456".into(),
            mount_path: Some("/mnt/mdt1".into()),
        };

        let deletions = Deletions(vec![&t]);

        let ups = vec![
            Target {
                state: "mounted".into(),
                name: "mdt2".into(),
                active_host_id: Some(2),
                host_ids: vec![1],
                filesystems: vec!["fs1".to_string()],
                uuid: "654321".into(),
                mount_path: Some("/mnt/mdt2".into()),
            },
            Target {
                state: "mounted".into(),
                name: "ost1".into(),
                active_host_id: Some(3),
                host_ids: vec![4],
                filesystems: vec!["fs1".to_string()],
                uuid: "567890".into(),
                mount_path: Some("/mnt/ost1".into()),
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
            active_host_id: Some(1),
            host_ids: vec![2],
            filesystems: vec!["fs1".into()],
            uuid: "123456".into(),
            mount_path: Some("/mnt/mdt1".into()),
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

    #[test]
    fn test_parse_target_filesystem_data() {
        let query_result = Some(vec![Node {
            statement_id: Some(0),
            series: Some(vec![Series {
                name: "target".to_string(),
                tags: Some(
                    vec![("target".to_string(), json!("fs-OST0000".to_string()))]
                        .into_iter()
                        .collect::<Map<String, Value>>(),
                ),
                columns: vec![
                    "time".into(),
                    "host".into(),
                    "target".into(),
                    "fs".into(),
                    "bytes_free".into(),
                ],
                values: vec![
                    vec![
                        json!(1597166951257510515 as i64),
                        json!("oss1"),
                        json!("fs-OST0009"),
                        json!("fs"),
                        json!(4913020928 as i64),
                    ],
                    vec![
                        json!(1597166951257510515 as i64),
                        json!("oss1"),
                        json!("fs-OST0008"),
                        json!("fs2"),
                        json!(4913020928 as i64),
                    ],
                ],
            }]),
        }]);

        let result = parse_filesystem_data(query_result, "fs");
        assert_eq!(
            result,
            vec![
                (
                    "fs-OST0009".to_string(),
                    vec![(Fqdn("oss1".to_string()), "fs".to_string())]
                ),
                (
                    "fs-OST0008".to_string(),
                    vec![(Fqdn("oss1".to_string()), "fs2".to_string())]
                ),
            ]
            .into_iter()
            .collect::<TargetFsRecord>(),
        );
    }

    #[test]
    fn test_parse_mgs_filesystem_data() {
        let query_result = Some(vec![Node {
            statement_id: Some(0),
            series: Some(vec![Series {
                name: "target".to_string(),
                tags: Some(
                    vec![("target".to_string(), json!("MGS".to_string()))]
                        .into_iter()
                        .collect::<Map<String, Value>>(),
                ),
                columns: vec![
                    "time".into(),
                    "host".into(),
                    "target".into(),
                    "mgs_fs".into(),
                ],
                values: vec![
                    vec![
                        json!(1597166951257510515 as i64),
                        json!("mds1"),
                        json!("MGS"),
                        json!("mgs1fs1,mgs1fs2"),
                    ],
                    vec![
                        json!(1597166951257510515 as i64),
                        json!("mds1"),
                        json!("MGS2"),
                        json!("mgs2fs1,mgs2fs2"),
                    ],
                ],
            }]),
        }]);

        let result = parse_filesystem_data(query_result, "mgs_fs");
        assert_eq!(
            result,
            vec![
                (
                    "MGS".to_string(),
                    vec![
                        (Fqdn("mds1".to_string()), "mgs1fs1".to_string()),
                        (Fqdn("mds1".to_string()), "mgs1fs2".to_string())
                    ]
                ),
                (
                    "MGS2".to_string(),
                    vec![
                        (Fqdn("mds1".to_string()), "mgs2fs1".to_string()),
                        (Fqdn("mds1".to_string()), "mgs2fs2".to_string())
                    ]
                ),
            ]
            .into_iter()
            .collect::<TargetFsRecord>(),
        );
    }

    #[test]
    fn test_parse_mgs_filesystem_data_on_separate_hosts() {
        let query_result = Some(vec![Node {
            statement_id: Some(0),
            series: Some(vec![Series {
                name: "target".to_string(),
                tags: None,
                columns: vec![
                    "time".into(),
                    "host".into(),
                    "target".into(),
                    "mgs_fs".into(),
                ],
                values: vec![
                    vec![
                        json!(1597166951257510515 as i64),
                        json!("mds1"),
                        json!("MGS"),
                        json!("fs1"),
                    ],
                    vec![
                        json!(1597166951257510515 as i64),
                        json!("oss1"),
                        json!("MGS"),
                        json!("fs2"),
                    ],
                ],
            }]),
        }]);

        let result = parse_filesystem_data(query_result, "mgs_fs");
        assert_eq!(
            result,
            vec![(
                "MGS".to_string(),
                vec![
                    (Fqdn("mds1".to_string()), "fs1".to_string()),
                    (Fqdn("oss1".to_string()), "fs2".to_string())
                ]
            ),]
            .into_iter()
            .collect::<TargetFsRecord>(),
        );
    }
}
