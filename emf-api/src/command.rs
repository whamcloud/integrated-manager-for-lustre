// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::error::EmfApiError;
use emf_postgres::{sqlx, PgPool};
use emf_wire_types::{db::Command as DbCommand, Command, EndpointName as _, TestHostJob};
use itertools::Itertools;

pub(crate) async fn get_command(pool: &PgPool, id: i32) -> Result<Command, EmfApiError> {
    let cmd = sqlx::query_as!(
        DbCommand,
        "SELECT * FROM chroma_core_command WHERE id = $1",
        id
    )
    .fetch_one(pool)
    .await?;

    let jobs = sqlx::query!(
        r#"
        SELECT * FROM chroma_core_job
        WHERE id IN (SELECT job_id from chroma_core_command_jobs
            WHERE command_id = $1)
    "#,
        id
    )
    .fetch_all(pool)
    .await?;

    let job_ids: Vec<i32> = jobs.iter().map(|x| x.id).collect();

    let steps = sqlx::query!(
        r#"
            SELECT * from chroma_core_stepresult
            WHERE job_id = ANY($1)
            ORDER BY modified_at DESC
    "#,
        &job_ids
    )
    .fetch_all(pool)
    .await?;

    Ok(Command {
        cancelled: cmd.cancelled,
        complete: cmd.complete,
        created_at: cmd.created_at.format("%Y-%m-%dT%T%.6f").to_string(),
        errored: cmd.errored,
        id: cmd.id,
        message: cmd.message,
        resource_uri: format!("/api/{}/{}/", Command::endpoint_name(), cmd.id),
        jobs: jobs
            .iter()
            .map(|j| format!("/api/{}/{}/", TestHostJob::endpoint_name(), j.id))
            .collect(),
        logs: steps.into_iter().map(|s| s.log).join("\n"),
    })
}
