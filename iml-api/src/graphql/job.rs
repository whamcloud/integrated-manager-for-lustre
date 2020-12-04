use crate::graphql::Context;
use chrono::{DateTime, Utc};
use futures::{lock::Mutex, TryFutureExt};
use iml_postgres::{sqlx, PgPool};
use iml_wire_types::{
    graphql::map::GraphQLMap, AvailableTransition, Command, EndpointName, Job, JobLock, Step,
};
use juniper::FieldError;
use once_cell::sync::Lazy;
use std::collections::HashMap;

static CONTENT_TYPES_CACHE: Lazy<Mutex<HashMap<i32, String>>> =
    Lazy::new(|| Mutex::new(HashMap::new()));

pub(crate) struct JobQuery;

#[derive(Clone, Debug)]
struct LockedItemType<'a>(&'a str);

#[juniper::graphql_object(Context = Context)]
impl JobQuery {
    /// Fetch the list of jobs
    #[graphql(arguments(ids(description = "The list of job ids to fetch, may be empty array"),))]
    async fn jobs_by_ids(
        context: &Context,
        ids: Vec<i32>,
    ) -> juniper::FieldResult<Vec<JobGraphQL>> {
        let content_types = ensure_cache_and_get_content_types(&context.pg_pool)
            .await?
            .lock()
            .await;
        let ids: &[i32] = &ids[..];
        let unordered_jobs: Vec<JobGraphQL> = sqlx::query_as!(
            JobRecord,
            r#"
                SELECT job.id,
                       array(SELECT cj.command_id
                             FROM chroma_core_command_jobs AS cj
                             WHERE cj.job_id = job.id) :: INT[] AS commands,
                       job.state,
                       job.errored,
                       job.cancelled,
                       job.modified_at,
                       job.created_at,
                       job.wait_for_json,
                       job.locks_json,
                       job.content_type_id,
                       job.class_name,
                       job.description_out,
                       job.cancellable_out,
                       array_agg(sr.id)::INT[]                  AS step_result_keys,
                       array_agg(sr.result)::TEXT[]             AS step_results_values
                FROM chroma_core_job AS job
                         JOIN chroma_core_command_jobs AS cj ON cj.job_id = job.id
                         JOIN chroma_core_stepresult AS sr ON sr.job_id = job.id
                WHERE (job.id = ANY ($1::INT[]))
                GROUP BY job.id
            "#,
            ids
        )
        .fetch_all(&context.pg_pool)
        .map_ok(|xs: Vec<JobRecord>| {
            xs.into_iter()
                .filter_map(|x| try_from_job_record(x, &content_types).ok())
                .collect::<Vec<JobGraphQL>>()
        })
        .await?;

        let mut hm = unordered_jobs
            .into_iter()
            .map(|x| (x.id, x))
            .collect::<HashMap<i32, JobGraphQL>>();
        let mut not_found = Vec::new();
        let jobs = ids
            .iter()
            .filter_map(|id| {
                hm.remove(id).or_else(|| {
                    not_found.push(id);
                    None
                })
            })
            .collect::<Vec<JobGraphQL>>();

        if !not_found.is_empty() {
            Err(FieldError::from(format!(
                "Jobs not found for ids: {:?}",
                not_found
            )))
        } else {
            Ok(jobs)
        }
    }
}

/// Concrete version of `iml_wire_types::Job<T>` needed for GraphQL
#[derive(serde::Serialize, serde::Deserialize, Clone, Debug, juniper::GraphQLObject)]
pub struct JobGraphQL {
    pub available_transitions: Vec<AvailableTransition>,
    pub cancelled: bool,
    pub class_name: String,
    pub commands: Vec<String>,
    pub created_at: String,
    pub description: String,
    pub errored: bool,
    pub id: i32,
    pub modified_at: String,
    pub read_locks: Vec<JobLock>,
    pub resource_uri: String,
    pub state: String,
    pub step_results: GraphQLMap,
    pub steps: Vec<String>,
    pub wait_for: Vec<String>,
    pub write_locks: Vec<JobLock>,
}

#[derive(Clone, Debug)]
pub struct JobRecord {
    pub id: i32,
    pub commands: Option<Vec<i32>>,
    pub state: String,
    pub errored: bool,
    pub cancelled: bool,
    pub modified_at: DateTime<Utc>,
    pub created_at: DateTime<Utc>,
    pub wait_for_json: String,
    pub locks_json: String,
    pub content_type_id: Option<i32>,
    pub step_result_keys: Option<Vec<i32>>,
    pub step_results_values: Option<Vec<String>>,
    pub class_name: String,
    pub description_out: String,
    pub cancellable_out: bool,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct JobLockUnresolved {
    pub uuid: String,
    pub locked_item_id: i32,
    pub locked_item_type_id: i32,
    pub write: bool,
    pub begin_state: Option<String>,
    pub end_state: Option<String>,
}

fn try_from_job_record(
    x: JobRecord,
    content_types: &HashMap<i32, String>,
) -> juniper::FieldResult<JobGraphQL> {
    let available_transitions = if x.state == "complete" || !x.cancellable_out {
        vec![]
    } else {
        vec![AvailableTransition {
            label: "Cancel".to_string(),
            state: "cancelled".to_string(),
        }]
    };
    let (read_locks, write_locks) = convert_job_locks(&x.locks_json, content_types)?;
    let commands = x
        .commands
        .unwrap_or_default()
        .into_iter()
        .map(|id| format!("/api/{}/{}/", Command::endpoint_name(), id))
        .collect();
    let wait_for = convert_job_wait_for(&x.wait_for_json)?;
    let step_results = convert_job_step_results(&x.step_result_keys, &x.step_results_values)?;
    let steps = x
        .step_result_keys
        .unwrap_or_default()
        .iter()
        .map(|id| format!("/api/{}/{}/", Step::endpoint_name(), id))
        .collect();
    let job = JobGraphQL {
        available_transitions,
        id: x.id,
        state: x.state,
        class_name: x.class_name,
        cancelled: x.cancelled,
        errored: x.errored,
        modified_at: x.modified_at.format("%Y-%m-%dT%T%.6f").to_string(),
        created_at: x.created_at.format("%Y-%m-%dT%T%.6f").to_string(),
        resource_uri: format!("/api/{}/{}/", Job::<()>::endpoint_name(), x.id),
        description: x.description_out,
        step_results,
        steps,
        wait_for,
        commands,
        read_locks,
        write_locks,
    };
    Ok(job)
}

fn convert_job_step_results(
    keys: &Option<Vec<i32>>,
    values: &Option<Vec<String>>,
) -> juniper::FieldResult<GraphQLMap> {
    let mut hm = HashMap::new();
    if let Some(keys) = keys {
        if let Some(values) = values {
            // we expect keys and values of the same size
            let n = usize::min(keys.len(), values.len());
            for i in 0..n {
                let k = format!("/api/{}/{}/", "step", keys[i]);
                let v = serde_json::from_str::<serde_json::Value>(&values[i])?;
                hm.insert(k, v);
            }
        }
    }
    Ok(GraphQLMap(hm))
}

fn convert_job_locks(
    locks_json: &str,
    content_types: &HashMap<i32, String>,
) -> juniper::FieldResult<(Vec<JobLock>, Vec<JobLock>)> {
    let locks = serde_json::from_str::<serde_json::Value>(locks_json)?;
    let mut read_locks = vec![];
    let mut write_locks = vec![];
    if let serde_json::Value::Array(raw_locks) = locks {
        for raw_lock in raw_locks {
            let lock_unresolved = serde_json::from_value::<JobLockUnresolved>(raw_lock)?;
            let item_type =
                convert_to_item_type(lock_unresolved.locked_item_type_id, content_types)?;
            let locked_item_id = lock_unresolved.locked_item_id;
            let locked_item_uri = item_type_to_uri(item_type, locked_item_id);
            let resource_uri = "".to_string();
            let lock = JobLock {
                locked_item_content_type_id: lock_unresolved.locked_item_type_id,
                locked_item_id,
                locked_item_uri,
                resource_uri,
            };
            if lock_unresolved.write {
                write_locks.push(lock);
            } else {
                read_locks.push(lock);
            }
        }
    };
    Ok((read_locks, write_locks))
}

fn convert_job_wait_for(json: &str) -> juniper::FieldResult<Vec<String>> {
    // json is a string like "[6, 7, 8, 9, 12, 13, 14]"
    let ids = serde_json::from_str::<serde_json::Value>(json)?;
    if let serde_json::Value::Array(ids) = ids {
        let wait_for = ids
            .into_iter()
            .flat_map(|x| x.as_i64())
            .map(|x| format!("/api/{}/{}/", Job::<()>::endpoint_name(), x))
            .collect::<Vec<String>>();
        Ok(wait_for)
    } else {
        Err(juniper::FieldError::from(format!(
            "Expected json array in '{}'",
            json
        )))
    }
}

async fn ensure_cache_and_get_content_types(
    pg_pool: &PgPool,
) -> juniper::FieldResult<&'static Mutex<HashMap<i32, String>>> {
    let mut guard = CONTENT_TYPES_CACHE.lock().await;
    if guard.is_empty() {
        let hm = load_content_types(pg_pool).await?;
        for (k, v) in hm {
            guard.insert(k, v);
        }
    }
    Ok(&CONTENT_TYPES_CACHE)
}

async fn load_content_types(pg_pool: &PgPool) -> juniper::FieldResult<HashMap<i32, String>> {
    // All _leaf_ python class names, derived from `chroma_core.models.jobs.StatefulObject`,
    // converted to lowercase. Must be synchronized with graphql::job::item_type_to_uri.
    let class_names = vec![
        "Copytool",
        "Corosync2Configuration",
        "CorosyncConfiguration",
        "FilesystemTicket",
        "LNetConfiguration",
        "LustreClientMount",
        "ManagedFilesystem",
        "ManagedHost",
        "ManagedMdt",
        "ManagedMgs",
        "ManagedOst",
        "ManagedTarget",
        "MasterTicket",
        "NTPConfiguration",
        "PacemakerConfiguration",
        "StratagemConfiguration",
        "Ticket",
    ]
    .into_iter()
    .map(|s| s.to_ascii_lowercase())
    .collect::<Vec<_>>();

    let names = &class_names[..];
    let content_types = sqlx::query!(
        r#"
            SELECT ct.id,
                   ct.model
            FROM django_content_type AS ct
            WHERE ct.app_label = 'chroma_core'
              AND ct.model = ANY ($1::VARCHAR[])
        "#,
        &names
    )
    .fetch_all(pg_pool)
    .map_ok(|xs| {
        xs.into_iter()
            .map(|x| (x.id, x.model))
            .collect::<Vec<(i32, String)>>()
    })
    .await?;
    let mut m = HashMap::new();
    for ct in content_types {
        m.insert(ct.0, ct.1);
    }
    Ok(m)
}

fn convert_to_item_type(
    id: i32,
    content_types: &HashMap<i32, String>,
) -> juniper::FieldResult<LockedItemType> {
    if let Some(t) = content_types.get(&id) {
        Ok(LockedItemType(&t))
    } else {
        Err(juniper::FieldError::from(format!(
            "Unknown lock type with id={}",
            id
        )))
    }
}

fn item_type_to_uri(lit: LockedItemType, id: i32) -> String {
    let resource_uri = match &lit.0[..] {
        "copytool" => "copytool",
        "corosync2configuration" => "corosync_configuration",
        "corosyncconfiguration" => "corosync_configuration",
        "filesystemticket" => "ticket",
        "lnetconfiguration" => "lnet_configuration",
        "lustreclientmount" => "client_mount",
        "managedfilesystem" => "filesystem",
        "managedhost" => "host",
        "managedmdt" => "target",
        "managedmgs" => "target",
        "managedost" => "target",
        "managedtarget" => "target",
        "masterticket" => "ticket",
        "ntpconfiguration" => "ntp_configuration",
        "pacemakerconfiguration" => "pacemaker_configuration",
        "stratagemconfiguration" => "stratagem_configuration",
        "ticket" => "ticket",
        _ => unreachable!("Impossible LockedItemType, see crate::graphql::job::NAMES list"),
    };
    format!("/api/{}/{}/", resource_uri, id)
}
