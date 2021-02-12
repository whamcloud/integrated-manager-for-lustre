// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::EmfDeviceError;
use emf_postgres::get_fs_target_resources;
use emf_tracing::tracing;
use emf_wire_types::TargetResource;
use futures::TryStreamExt;
use lazy_static::lazy_static;
use regex::Regex;
use sqlx::{postgres::PgPool, Postgres, Transaction};
use std::collections::{BTreeSet, HashMap, HashSet};

#[derive(Default)]
struct FsParts<'a> {
    mgs: Option<&'a TargetResource>,
    mdts: HashSet<&'a TargetResource>,
    osts: HashSet<&'a TargetResource>,
}

impl<'a> FsParts<'a> {
    fn is_fs(&self) -> bool {
        self.mgs.is_some() && !self.mdts.is_empty() && !self.osts.is_empty()
    }
}

type Filesystems<'a> = HashMap<String, FsParts<'a>>;

pub async fn learn(pool: &PgPool) -> Result<(), EmfDeviceError> {
    let mut xs = get_fs_target_resources(pool, None).await?;

    // If HA is not present, we will just use the targets directly
    if xs.is_empty() {
        xs = sqlx::query!(
            r#"
                SELECT
                    name,
                    mount_path,
                    filesystems,
                    uuid,
                    state,
                    id
                FROM target
                WHERE CARDINALITY(filesystems) > 0"#
        )
        .fetch(pool)
        .map_ok(|x| TargetResource {
            cluster_id: 0,
            target_id: x.id,
            fs_names: x.filesystems,
            uuid: x.uuid,
            name: x.name,
            resource_id: "".to_string(),
            state: x.state,
            cluster_hosts: vec![],
        })
        .try_collect()
        .await?;
    }

    let fss: Filesystems =
        xs.iter()
            .filter(|x| x.state == "mounted")
            .fold(HashMap::new(), |mut acc, x| {
                for f in x.fs_names.as_slice() {
                    let mut parts = acc.entry(f.to_string()).or_insert_with(FsParts::default);

                    match x.name.as_str() {
                        "MGS" => parts.mgs = Some(x),
                        name if name.contains("-MDT") => {
                            parts.mdts.insert(x);
                        }
                        name if name.contains("-OST") => {
                            parts.osts.insert(x);
                        }
                        name => {
                            tracing::debug!("detect miss on name: {}", name);
                        }
                    }
                }

                acc
            });

    let tickets = sqlx::query!(
        r#"
            SELECT cluster_id, name, active
            FROM corosync_resource
            WHERE resource_agent = 'ocf::ddn:Ticketer';
            "#
    )
    .fetch(pool)
    .try_fold(HashMap::new(), |mut acc, x| async {
        let xs = acc.entry(x.cluster_id).or_insert_with(HashSet::new);

        xs.insert((x.name, x.active));

        Ok(acc)
    })
    .await?;

    let mut transaction = pool.begin().await?;

    for (fs, parts) in fss {
        let mgs = match parts.mgs {
            Some(x) => x,
            None => continue,
        };

        if !parts.is_fs() {
            continue;
        }

        let state = get_fs_state(&parts);

        let fs_id = upsert_managed_filesystem(
            &mut transaction,
            &fs,
            mgs.target_id,
            &parts.mdts,
            &parts.osts,
            &state,
        )
        .await?;

        let tickets = tickets.get(&mgs.cluster_id);

        let tickets = match tickets {
            Some(x) => x,
            None => continue,
        };

        let fs_ticket = tickets.iter().find(|(x, _)| &fs == x);

        if let Some((_, active)) = fs_ticket {
            let id = upsert_ticket(&mut transaction, &fs, *active, mgs.cluster_id).await?;

            sqlx::query!(
                r#"
                        INSERT INTO filesystemticket
                            (ticket_ptr_id, filesystem_id)
                            VALUES
                            ($1, $2)
                            ON CONFLICT (ticket_ptr_id)
                            DO UPDATE SET
                            filesystem_id = EXCLUDED.filesystem_id
                    "#,
                id,
                fs_id
            )
            .execute(&mut transaction)
            .await?;
        }

        let lustre_ticket = tickets.iter().find(|(x, _)| &"lustre" == x);

        if let Some((_, active)) = lustre_ticket {
            let id = upsert_ticket(&mut transaction, "lustre", *active, mgs.cluster_id).await?;

            sqlx::query!(
                r#"
                    INSERT INTO masterticket
                    (ticket_ptr_id, mgs_id) 
                    VALUES
                    ($1, $2)
                    ON CONFLICT (ticket_ptr_id)
                    DO UPDATE SET
                    mgs_id = EXCLUDED.mgs_id
                "#,
                id,
                mgs.target_id
            )
            .execute(&mut transaction)
            .await?;
        }
    }

    transaction.commit().await?;

    Ok(())
}

fn get_fs_state(parts: &FsParts) -> String {
    let x = parts
        .mgs
        .as_ref()
        .map(|x| vec![x])
        .unwrap_or(vec![])
        .into_iter()
        .chain(&parts.mdts)
        .chain(&parts.osts)
        .fold(HashMap::new(), |mut acc, x| {
            acc.insert(&x.name, &x.state);

            acc
        });

    let is_stopped = x.values().all(|x| x.as_str() == "unmounted");

    let is_unavailable = x
        .iter()
        .filter(|(k, _)| k.ends_with("-MDT0000"))
        .filter(|(_, v)| v.as_str() == "unmounted")
        .next()
        .is_some();

    if is_stopped {
        "stopped"
    } else if is_unavailable {
        "unavailable"
    } else {
        "available"
    }
    .to_string()
}

async fn find_ticket_by_label(
    label: &str,
    t: &mut Transaction<'_, Postgres>,
) -> Result<Option<i32>, EmfDeviceError> {
    let id = sqlx::query!("SELECT id FROM ticket WHERE ha_label = $1", &label)
        .fetch_optional(t)
        .await?
        .map(|x| x.id);

    Ok(id)
}

async fn upsert_ticket(
    t: &mut Transaction<'_, Postgres>,
    label: &str,
    active: bool,
    cluster_id: i32,
) -> Result<i32, EmfDeviceError> {
    let id = find_ticket_by_label(label, t).await?;

    let state = if active { "granted" } else { "revoked" };

    if let Some(id) = id {
        sqlx::query!(
            r#"
            UPDATE ticket SET
                state_modified_at = now(),
                state = $1,
                name = $2,
                ha_label = $2,
                resource_controlled = 't',
                cluster_id = $3
            WHERE id = $4
        "#,
            state,
            label,
            cluster_id,
            id
        )
        .execute(t)
        .await?;

        return Ok(id);
    } else {
        let id = sqlx::query!(
            r#"
        INSERT INTO ticket (
                state_modified_at,
                state,
                ha_label,
                name,
                resource_controlled,
                cluster_id
            ) VALUES (now(), $1, $2, $2, 't', $3)
        RETURNING id
        "#,
            state,
            label,
            cluster_id,
        )
        .fetch_one(t)
        .await?
        .id;

        Ok(id)
    }
}

async fn find_managed_fs_id_by_name(
    name: &str,
    t: &mut Transaction<'_, Postgres>,
) -> Result<Option<i32>, EmfDeviceError> {
    let id = sqlx::query!("SELECT id FROM filesystem WHERE name = $1", &name)
        .fetch_optional(t)
        .await?
        .map(|x| x.id);

    Ok(id)
}

async fn upsert_managed_filesystem<'a>(
    t: &mut Transaction<'_, Postgres>,
    fsname: &str,
    mgs_id: i32,
    mdts: &HashSet<&'a TargetResource>,
    osts: &HashSet<&'a TargetResource>,
    state: &str,
) -> Result<i32, EmfDeviceError> {
    let id = find_managed_fs_id_by_name(fsname, t).await?;

    let max_mdt_idx = get_largest_idx(&mdts)?;
    let max_ost_idx = get_largest_idx(&osts)?;

    let mdt_ids: Vec<_> = mdts.into_iter().map(|x| x.target_id).collect();
    let ost_ids: Vec<_> = osts.into_iter().map(|x| x.target_id).collect();

    if let Some(id) = id {
        sqlx::query!(
            r#"
                UPDATE filesystem SET
                    state_modified_at = now(),
                    state = 'available',
                    mgs_id = $1
            "#,
            mgs_id,
        )
        .execute(t)
        .await?;

        return Ok(id);
    } else {
        let id = sqlx::query!(
            r#"
                    INSERT INTO filesystem (
                        state,
                        name,
                        mdt_next_index,
                        ost_next_index,
                        mgs_id,
                        mdt_ids,
                        ost_ids
                    ) VALUES (
                        $1,
                        $2,
                        $3,
                        $4,
                        $5,
                        $6,
                        $7
                    )
                    RETURNING id
                "#,
            state,
            fsname,
            max_mdt_idx + 1,
            max_ost_idx + 1,
            mgs_id,
            &mdt_ids,
            &ost_ids
        )
        .fetch_one(t)
        .await?
        .id;

        return Ok(id);
    }
}

fn get_target_idx(name: &str) -> Option<i32> {
    lazy_static! {
        static ref RE: Regex = Regex::new(r"[\w\-]+-\w+([0-9a-f]{4})$").unwrap();
    }

    let caps = RE.captures(name)?;

    let idx = caps.get(1)?.as_str();

    let idx = i32::from_str_radix(idx, 16).ok()?;

    Some(idx)
}

fn try_get_target_idx(name: &str) -> Result<i32, EmfDeviceError> {
    get_target_idx(name).ok_or_else(|| EmfDeviceError::TargetIndexNotFoundError(name.to_string()))
}

fn get_largest_idx(xs: &HashSet<&TargetResource>) -> Result<i32, EmfDeviceError> {
    let xs = xs
        .into_iter()
        .map(|x| try_get_target_idx(&x.name))
        .collect::<Result<BTreeSet<_>, EmfDeviceError>>()?;

    Ok(xs.into_iter().max().unwrap_or_default())
}
