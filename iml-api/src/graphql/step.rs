use crate::graphql::Context;
use chrono::{DateTime, Utc};
use futures::TryFutureExt;
use iml_postgres::sqlx;
use iml_wire_types::graphql::map::GraphQLMap;
use iml_wire_types::{Command, EndpointName};
use juniper::{DefaultScalarValue, FieldError};
use std::collections::HashMap;
use std::convert::TryFrom;

pub(crate) struct StepQuery;

#[juniper::graphql_object(Context = Context)]
impl StepQuery {
    /// Fetch the list of steps
    #[graphql(arguments(ids(description = "The list of step ids to fetch, may be empty array")))]
    async fn steps_by_ids(
        context: &Context,
        ids: Vec<i32>,
    ) -> juniper::FieldResult<Vec<StepGraphQL>> {
        let ids: &[i32] = &ids[..];
        let unordered_steps: Vec<StepGraphQL> = sqlx::query_as!(
            StepRecord,
            r#"
                SELECT sr.created_at,
                    sr.backtrace,
                    sr.console,
                    sr.id,
                    sr.description,
                    sr.step_index,
                    sr.log,
                    sr.class_name,
                    sr.job_id,
                    sr.modified_at,
                    sr.state,
                    sr.result,
                    sr.args_json,
                    sr.step_count
                FROM chroma_core_stepresult as sr
                WHERE (sr.id = ANY ($1::INT[]))
            "#,
            ids
        )
        .fetch_all(&context.pg_pool)
        .map_ok(|xs: Vec<StepRecord>| {
            xs.into_iter()
                .filter_map(|x| StepGraphQL::try_from(x).ok())
                .collect::<Vec<StepGraphQL>>()
        })
        .await?;

        let mut hm = unordered_steps
            .into_iter()
            .map(|x| (x.id, x))
            .collect::<HashMap<i32, StepGraphQL>>();
        let mut not_found = Vec::new();
        let jobs = ids
            .iter()
            .filter_map(|id| {
                hm.remove(id).or_else(|| {
                    not_found.push(id);
                    None
                })
            })
            .collect::<Vec<StepGraphQL>>();

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

/// Concrete version of `iml_wire_types::Step` needed for GraphQL
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize, juniper::GraphQLObject)]
pub struct StepGraphQL {
    pub args: GraphQLMap,
    pub backtrace: String,
    pub class_name: String,
    pub console: String,
    pub created_at: String,
    pub description: String,
    pub id: i32,
    pub log: String,
    pub modified_at: String,
    pub resource_uri: String,
    pub result: Option<String>,
    pub state: String,
    pub step_count: i32,
    pub step_index: i32,
}

#[derive(Debug, Clone)]
pub struct StepRecord {
    pub backtrace: String,
    pub console: String,
    pub created_at: DateTime<Utc>,
    pub id: i32,
    pub log: String,
    pub modified_at: DateTime<Utc>,
    pub result: Option<String>,
    pub job_id: i32,
    pub state: String,
    pub step_count: i32,
    pub step_index: i32,
    pub class_name: String,
    pub args_json: String,
    pub description: String,
}

impl TryFrom<StepRecord> for StepGraphQL {
    type Error = FieldError<DefaultScalarValue>;

    fn try_from(x: StepRecord) -> juniper::FieldResult<Self> {
        let args = serde_json::from_str::<HashMap<String, serde_json::Value>>(&x.args_json)?;
        let step = StepGraphQL {
            args: GraphQLMap(args),
            backtrace: x.backtrace,
            class_name: x.class_name,
            console: x.console,
            created_at: x.created_at.format("%Y-%m-%dT%T%.6f").to_string(),
            description: x.description,
            id: x.id,
            log: x.log,
            modified_at: x.modified_at.format("%Y-%m-%dT%T%.6f").to_string(),
            resource_uri: format!("/api/{}/{}/", Command::endpoint_name(), x.id),
            result: x.result,
            state: x.state,
            step_count: x.step_count,
            step_index: x.step_index,
        };
        Ok(step)
    }
}
