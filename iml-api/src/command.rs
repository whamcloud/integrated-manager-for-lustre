// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::error::ImlApiError;
use iml_orm::{
    command::ChromaCoreCommand,
    job::ChromaCoreJob,
    step::ChromaCoreStepresult,
    tokio_diesel::{AsyncRunQueryDsl as _, OptionalExtension as _},
    DbPool,
};
use iml_wire_types::{Command, EndpointName as _, TestHostJob};
use itertools::Itertools;

pub(crate) async fn get_command(pool: &DbPool, id: i32) -> Result<Command, ImlApiError> {
    let cmd: ChromaCoreCommand = ChromaCoreCommand::by_id(id)
        .first_async(&pool)
        .await
        .optional()?
        .ok_or_else(|| ImlApiError::NoneError)?;

    let jobs: Vec<ChromaCoreJob> = ChromaCoreJob::by_cmdjob(id)
        .get_results_async(&pool)
        .await?;

    let steps: Vec<ChromaCoreStepresult> = ChromaCoreStepresult::by_jobs(jobs.iter().map(|j| j.id))
        .get_results_async(&pool)
        .await?;

    Ok(Command {
        cancelled: cmd.cancelled,
        complete: cmd.complete,
        created_at: format!("{}", cmd.created_at),
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
