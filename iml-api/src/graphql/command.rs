use crate::graphql::Context;
use chrono::{DateTime, Utc};
use futures::TryFutureExt;
use iml_postgres::sqlx;
use iml_wire_types::Command;
use iml_wire_types::EndpointName;
use iml_wire_types::Job;
use iml_wire_types::SortDir;
use juniper::FieldError;
use std::collections::HashMap;
use std::ops::Deref;

pub(crate) struct CommandQuery;

#[juniper::graphql_object(Context = Context)]
impl CommandQuery {
    /// Fetch the list of commands
    #[graphql(arguments(
        limit(description = "optional paging limit, defaults to all rows"),
        offset(description = "Offset into items, defaults to 0"),
        dir(description = "Sort direction, defaults to ASC"),
        is_active(description = "Command status, active means not completed, default is true"),
        msg(description = "Substring of the command's message, null or empty matches all"),
    ))]
    async fn commands(
        context: &Context,
        limit: Option<i32>,
        offset: Option<i32>,
        dir: Option<SortDir>,
        is_active: Option<bool>,
        msg: Option<String>,
    ) -> juniper::FieldResult<Vec<Command>> {
        let dir = dir.unwrap_or_default();
        let is_completed = !is_active.unwrap_or(true);
        let commands: Vec<Command> = sqlx::query_as!(
            CommandRecord,
            r#"
                SELECT
                    c.id AS id,
                    cancelled,
                    complete,
                    errored,
                    created_at,
                    array_agg(cj.job_id)::INT[] AS job_ids,
                    message
                FROM chroma_core_command c
                JOIN chroma_core_command_jobs cj ON c.id = cj.command_id
                WHERE ($4::BOOL IS NULL OR complete = $4)
                  AND ($5::TEXT IS NULL OR c.message ILIKE '%' || $5 || '%')
                GROUP BY c.id
                ORDER BY
                    CASE WHEN $3 = 'ASC' THEN c.id END ASC,
                    CASE WHEN $3 = 'DESC' THEN c.id END DESC
                OFFSET $1 LIMIT $2
            "#,
            offset.unwrap_or(0) as i64,
            limit.map(|x| x as i64),
            dir.deref(),
            is_completed,
            msg,
        )
        .fetch_all(&context.pg_pool)
        .map_ok(|xs: Vec<CommandRecord>| xs.into_iter().map(|x| x.into()).collect::<Vec<Command>>())
        .await?;
        Ok(commands)
    }

    /// Fetch the list of commands by ids, the returned
    /// collection is guaranteed to match the input.
    /// If a command not found, `None` is returned for that index.
    #[graphql(arguments(ids(description = "The list of command ids to fetch, ids may be empty"),))]
    async fn commands_by_ids(
        context: &Context,
        ids: Vec<i32>,
    ) -> juniper::FieldResult<Vec<Command>> {
        let ids: &[i32] = &ids[..];
        let unordered_cmds: Vec<Command> = sqlx::query_as!(
            CommandRecord,
            r#"
                SELECT
                    c.id AS id,
                    cancelled,
                    complete,
                    errored,
                    created_at,
                    array_agg(cj.job_id)::INT[] AS job_ids,
                    message
                FROM chroma_core_command c
                JOIN chroma_core_command_jobs cj ON c.id = cj.command_id
                WHERE (c.id = ANY ($1::INT[]))
                GROUP BY c.id
            "#,
            ids,
        )
        .fetch_all(&context.pg_pool)
        .map_ok(|xs: Vec<CommandRecord>| xs.into_iter().map(|x| x.into()).collect::<Vec<Command>>())
        .await?;

        let mut hm = unordered_cmds
            .into_iter()
            .map(|x| (x.id, x))
            .collect::<HashMap<i32, Command>>();
        let mut not_found = Vec::new();
        let commands = ids
            .iter()
            .filter_map(|id| {
                hm.remove(id).or_else(|| {
                    not_found.push(id);
                    None
                })
            })
            .collect::<Vec<Command>>();

        if !not_found.is_empty() {
            Err(FieldError::from(format!(
                "Commands not found for ids: {:?}",
                not_found
            )))
        } else {
            Ok(commands)
        }
    }
}

#[derive(serde::Serialize, serde::Deserialize, Clone, Debug)]
struct CommandRecord {
    pub cancelled: bool,
    pub complete: bool,
    pub created_at: DateTime<Utc>,
    pub errored: bool,
    pub id: i32,
    pub job_ids: Option<Vec<i32>>,
    pub message: String,
}

impl From<CommandRecord> for Command {
    fn from(x: CommandRecord) -> Self {
        Self {
            id: x.id,
            cancelled: x.cancelled,
            complete: x.complete,
            errored: x.errored,
            created_at: x.created_at.format("%Y-%m-%dT%T%.6f").to_string(),
            jobs: {
                x.job_ids
                    .unwrap_or_default()
                    .into_iter()
                    .map(|job_id: i32| format!("/api/{}/{}/", Job::<()>::endpoint_name(), job_id))
                    .collect::<Vec<_>>()
            },
            logs: "".to_string(),
            message: x.message.clone(),
            resource_uri: format!("/api/{}/{}/", Command::endpoint_name(), x.id),
        }
    }
}
