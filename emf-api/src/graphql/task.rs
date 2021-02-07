// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    error::EmfApiError,
    graphql::{create_task_job, fs_id_by_name, insert_task, Context, SendJob},
};
use emf_postgres::sqlx;
use emf_wire_types::{
    task::{Task, TaskArgs, TaskOut},
    Command,
};
use futures::TryStreamExt;
use std::{collections::HashMap, convert::TryInto};

pub(crate) struct TaskQuery;

#[juniper::graphql_object(Context = Context)]
impl TaskQuery {
    /// List all known `Task` records.
    async fn list(context: &Context) -> juniper::FieldResult<Vec<TaskOut>> {
        let xs = sqlx::query_as!(Task, "SELECT * FROM task")
            .fetch(&context.pg_pool)
            .err_into::<EmfApiError>()
            .and_then(|x| async {
                let x = x.try_into()?;

                Ok(x)
            })
            .try_collect()
            .await?;

        Ok(xs)
    }
}

#[derive(juniper::GraphQLObject)]
pub struct CreateTaskResult {
    task_id: i32,
    command: Command,
}

pub(crate) struct TaskMutation;

#[juniper::graphql_object(Context = Context)]
impl TaskMutation {
    /// Create a new task
    async fn create(
        context: &Context,
        fsname: String,
        task_args: TaskArgs,
    ) -> juniper::FieldResult<CreateTaskResult> {
        let fs_id = fs_id_by_name(&context.pg_pool, &fsname).await?;

        let args: HashMap<String, String> = task_args
            .pairs
            .into_iter()
            .map(|x| (x.key, x.value))
            .collect();

        let task = insert_task(
            &task_args.name,
            "created",
            task_args.single_runner,
            task_args.keep_failed,
            &task_args.actions,
            serde_json::to_value(&args)?,
            fs_id,
            &context.pg_pool,
        )
        .await?;

        let job = create_task_job(task.id);

        unimplemented!();
    }
    /// Remove an existing task by id
    async fn remove(context: &Context, task_id: i32) -> juniper::FieldResult<Command> {
        let job = SendJob {
            class_name: "RemoveTaskJob",
            args: vec![("task_id".into(), serde_json::json!(task_id))]
                .into_iter()
                .collect::<HashMap<String, serde_json::Value>>(),
        };

        unimplemented!();
    }
}
