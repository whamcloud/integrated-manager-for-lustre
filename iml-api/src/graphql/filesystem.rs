// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    error::ImlApiError,
    graphql::{authorize, get_fs_target_resources, Context, TargetResource},
};
use futures::TryStreamExt;
use iml_postgres::sqlx::{self, Postgres, Transaction};
use juniper::{FieldError, Value};
use lazy_static::lazy_static;
use regex::Regex;
use std::collections::{HashMap, HashSet};

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

pub(crate) struct FilesystemMutation;

#[juniper::graphql_object(Context = Context)]
impl FilesystemMutation {
    async fn detect(context: &Context) -> juniper::FieldResult<bool> {
        if authorize(
            &context.enforcer,
            &context.session,
            "mutation::filesystem::detect",
        )? {
            let mut xs = get_fs_target_resources(&context.pg_pool, None).await?;

            // If HA is not present, we will just use the targets directly
            if xs.is_empty() {
                xs = sqlx::query!(
                    r#"
                SELECT
                    name,
                    mount_path,
                    filesystems,
                    uuid,
                    state
                FROM target
                WHERE CARDINALITY(filesystems) > 0"#
                )
                .fetch(&context.pg_pool)
                .map_ok(|x| TargetResource {
                    cluster_id: 0,
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

            let content_types = sqlx::query!(
            r#"
                SELECT id, model FROM django_content_type
                WHERE app_label = 'chroma_core'
                AND model IN ('managedfilesystem','managedmdt','managedmgs','managedost', 'filesystemticket', 'masterticket')
            "#
        )
        .fetch(&context.pg_pool)
        .try_fold(HashMap::new(), |mut acc, x| async {
            acc.insert(x.model, x.id);

            Ok(acc)
        })
        .await?;

            let fs_content_type = get_content_type(&content_types, "managedfilesystem")?;

            let mgs_content_type = get_content_type(&content_types, "managedmgs")?;

            let mdt_content_type = get_content_type(&content_types, "managedmdt")?;

            let ost_content_type = get_content_type(&content_types, "managedost")?;

            let fs_ticket_content_type = get_content_type(&content_types, "filesystemticket")?;

            let master_ticket_content_type = get_content_type(&content_types, "masterticket")?;

            let fss: Filesystems =
                xs.iter()
                    .filter(|x| x.state == "mounted")
                    .fold(HashMap::new(), |mut acc, x| {
                        for f in x.fs_names.as_slice() {
                            let mut parts =
                                acc.entry(f.to_string()).or_insert_with(FsParts::default);

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
            .fetch(&context.pg_pool)
            .try_fold(HashMap::new(), |mut acc, x| async {
                let xs = acc.entry(x.cluster_id).or_insert_with(HashSet::new);

                xs.insert((x.name, x.active));

                Ok(acc)
            })
            .await?;

            let mut transaction = context.pg_pool.begin().await?;

            for (fs, parts) in fss {
                let mgs = match parts.mgs {
                    Some(x) => x,
                    None => continue,
                };

                let mgs_id = upsert_managed_target(&mut transaction, mgs, mgs_content_type).await?;

                sqlx::query!(
                    r#"
                    INSERT INTO chroma_core_managedmgs
                    VALUES ($1, 0, 0)
                    ON CONFLICT (managedtarget_ptr_id) DO NOTHING
                "#,
                    mgs_id
                )
                .execute(&mut transaction)
                .await?;

                if !parts.is_fs() {
                    continue;
                }

                let fs_id =
                    upsert_managed_filesystem(&mut transaction, &fs, fs_content_type, mgs_id)
                        .await?;

                for mdt in parts.mdts {
                    let idx = get_target_idx(&mdt.name).ok_or_else(|| {
                        FieldError::new(
                            format!("Detect Failed, could not find index for MDT {}", &mdt.name),
                            Value::null(),
                        )
                    })?;

                    let id = upsert_managed_target(&mut transaction, mdt, mdt_content_type).await?;

                    sqlx::query!(
                        r#"
                        INSERT INTO chroma_core_managedmdt VALUES ($1, $2, $3)
                        ON CONFLICT (managedtarget_ptr_id) DO NOTHING
                    "#,
                        id,
                        idx,
                        fs_id
                    )
                    .execute(&mut transaction)
                    .await?;
                }

                for ost in parts.osts {
                    let idx = get_target_idx(&ost.name).ok_or_else(|| {
                        FieldError::new(
                            format!("Detect Failed, could not find index for OST {}", &ost.name),
                            Value::null(),
                        )
                    })?;

                    let id = upsert_managed_target(&mut transaction, ost, ost_content_type).await?;

                    sqlx::query!(
                        r#"
                        INSERT INTO chroma_core_managedost VALUES ($1, $2, $3)
                        ON CONFLICT (managedtarget_ptr_id) DO NOTHING
                    "#,
                        id,
                        idx,
                        fs_id
                    )
                    .execute(&mut transaction)
                    .await?;
                }

                sqlx::query!(
                r#"
                    UPDATE chroma_core_managedfilesystem f
                    SET mdt_next_index = (SELECT MAX(index) + 1 FROM chroma_core_managedmdt WHERE filesystem_id = $1),
                    ost_next_index = (SELECT MAX(index) + 1 FROM chroma_core_managedost WHERE filesystem_id = $1)
                    where id = $1"#,
                fs_id
            )
            .execute(&mut transaction)
            .await?;

                let tickets = tickets.get(&mgs.cluster_id);

                let tickets = match tickets {
                    Some(x) => x,
                    None => continue,
                };

                let fs_ticket = tickets.iter().find(|(x, _)| &fs == x);

                if let Some((_, active)) = fs_ticket {
                    let id = upsert_ticket(
                        &mut transaction,
                        &fs,
                        *active,
                        mgs.cluster_id,
                        fs_ticket_content_type,
                    )
                    .await?;

                    sqlx::query!(
                        r#"
                        INSERT INTO chroma_core_filesystemticket
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
                    let id = upsert_ticket(
                        &mut transaction,
                        "lustre",
                        *active,
                        mgs.cluster_id,
                        master_ticket_content_type,
                    )
                    .await?;

                    sqlx::query!(
                        r#"
                    INSERT INTO chroma_core_masterticket
                    (ticket_ptr_id, mgs_id) 
                    VALUES
                    ($1, $2)
                    ON CONFLICT (ticket_ptr_id)
                    DO UPDATE SET
                    mgs_id = EXCLUDED.mgs_id
                "#,
                        id,
                        mgs_id
                    )
                    .execute(&mut transaction)
                    .await?;
                }
            }

            transaction.commit().await?;

            Ok(true)
        } else {
            Err(FieldError::new("Not authorized", Value::null()))
        }
    }
}

async fn find_managed_fs_id_by_name(
    name: &str,
    t: &mut Transaction<'_, Postgres>,
) -> Result<Option<i32>, ImlApiError> {
    let id = sqlx::query!(
        "SELECT id FROM chroma_core_managedfilesystem WHERE name = $1 AND not_deleted = 't'",
        &name
    )
    .fetch_optional(t)
    .await?
    .map(|x| x.id);

    Ok(id)
}

async fn upsert_managed_filesystem(
    t: &mut Transaction<'_, Postgres>,
    fsname: &str,
    fs_content_type: i32,
    mgs_id: i32,
) -> Result<i32, ImlApiError> {
    let id = find_managed_fs_id_by_name(fsname, t).await?;

    if let Some(id) = id {
        sqlx::query!(
            r#"
                UPDATE chroma_core_managedfilesystem SET
                    state_modified_at = now(),
                    state = 'available',
                    immutable_state = 'f',
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
                    INSERT INTO chroma_core_managedfilesystem (
                        state_modified_at,
                        state,
                        immutable_state,
                        name,
                        mdt_next_index,
                        ost_next_index,
                        not_deleted,
                        content_type_id,
                        mgs_id
                    ) VALUES (
                        now(),
                        'available',
                        'f',
                        $1,
                        1,
                        1,
                        't',
                        $2,
                        $3
                    )
                    RETURNING id
                "#,
            fsname,
            fs_content_type,
            mgs_id
        )
        .fetch_one(t)
        .await?
        .id;

        return Ok(id);
    }
}

async fn find_managed_target_id_by_name_uuid(
    name: &str,
    uuid: &str,
    t: &mut Transaction<'_, Postgres>,
) -> Result<Option<i32>, ImlApiError> {
    let id = sqlx::query!(
        "SELECT id FROM chroma_core_managedtarget WHERE name = $1 AND uuid = $2 AND not_deleted = 't'",
        name,
        &uuid
    )
    .fetch_optional(t)
    .await?
    .map(|x| x.id);

    Ok(id)
}

async fn upsert_managed_target(
    t: &mut Transaction<'_, Postgres>,
    x: &TargetResource,
    content_type_id: i32,
) -> Result<i32, ImlApiError> {
    let id = find_managed_target_id_by_name_uuid(&x.name, &x.uuid, t).await?;

    let resource_id = if x.resource_id.is_empty() {
        None
    } else {
        Some(x.resource_id.to_string())
    };

    if let Some(id) = id {
        sqlx::query!(
            r#"
            UPDATE chroma_core_managedtarget SET
                state_modified_at = now(),
                state = 'mounted',
                immutable_state = 'f',
                ha_label = $2,
                reformat = 'f',
                content_type_id = $3
            WHERE name = $1 AND uuid = $4
        "#,
            x.name,
            resource_id,
            content_type_id,
            x.uuid
        )
        .execute(t)
        .await?;

        return Ok(id);
    } else {
        let id = sqlx::query!(
            r#"
        INSERT INTO chroma_core_managedtarget (
                state_modified_at,
                state,
                immutable_state,
                name,
                uuid,
                ha_label,
                reformat,
                not_deleted,
                content_type_id
            ) VALUES (now(), 'mounted', 'f', $1, $2, $3, 'f', 't', $4)
        RETURNING id
        "#,
            x.name,
            x.uuid,
            resource_id,
            content_type_id
        )
        .fetch_one(t)
        .await?
        .id;

        return Ok(id);
    }
}

async fn find_ticket_by_label(
    label: &str,
    t: &mut Transaction<'_, Postgres>,
) -> Result<Option<i32>, ImlApiError> {
    let id = sqlx::query!(
        "SELECT id FROM chroma_core_ticket WHERE ha_label = $1 AND not_deleted = 't'",
        &label
    )
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
    content_type_id: i32,
) -> Result<i32, ImlApiError> {
    let id = find_ticket_by_label(label, t).await?;

    let state = if active { "granted" } else { "revoked" };

    if let Some(id) = id {
        sqlx::query!(
            r#"
            UPDATE chroma_core_ticket SET
                state_modified_at = now(),
                state = $1,
                immutable_state = 'f',
                name = $2,
                ha_label = $2,
                resource_controlled = 't',
                cluster_id = $3,
                content_type_id = $4
            WHERE id = $5
        "#,
            state,
            label,
            cluster_id,
            content_type_id,
            id
        )
        .execute(t)
        .await?;

        return Ok(id);
    } else {
        let id = sqlx::query!(
            r#"
        INSERT INTO chroma_core_ticket (
                state_modified_at,
                state,
                immutable_state,
                ha_label,
                name,
                resource_controlled,
                not_deleted,
                cluster_id,
                content_type_id
            ) VALUES (now(), $1, 'f', $2, $2, 't', 't', $3, $4)
        RETURNING id
        "#,
            state,
            label,
            cluster_id,
            content_type_id
        )
        .fetch_one(t)
        .await?
        .id;

        Ok(id)
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

fn get_content_type(x: &HashMap<String, i32>, name: &str) -> juniper::FieldResult<i32> {
    let x = x.get(name).ok_or_else(|| {
        FieldError::new(
            format!("Could not find content type for {}", name),
            Value::null(),
        )
    })?;

    Ok(*x)
}
