use std::collections::HashMap;
use chrono::{DateTime, Utc};
use iml_wire_types::{Command, EndpointName};
use std::convert::TryFrom;
use juniper::{
    DefaultScalarValue,
    FieldError,
};
use crate::graphql_map::GraphQLMap;

/// Concrete version of `iml_wire_types::Step` needed for GraphQL
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
#[derive(juniper::GraphQLObject)]
pub struct StepGQL {
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

impl TryFrom<StepRecord> for StepGQL {
    type Error = FieldError<DefaultScalarValue>;

    fn try_from(x: StepRecord) -> juniper::FieldResult<Self> {
        let args = serde_json::from_str::<HashMap<String, serde_json::Value>>(&x.args_json)?;
        let step = StepGQL {
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
