// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::error::ImlApiError;
use futures::TryFutureExt;
use iml_orm::{
    command::ChromaCoreCommand,
    job::{get_jobs_by_cmd, ChromaCoreJob},
    step::ChromaCoreStepresult,
    tokio_diesel::AsyncRunQueryDsl as _,
    DbPool,
};
use iml_wire_types::{Command, EndpointName as _, TestHostJob};
use itertools::Itertools;

pub(crate) async fn get_command(pool: &DbPool, id: i32) -> Result<Command, ImlApiError> {
    let mut cmd: Vec<ChromaCoreCommand> = ChromaCoreCommand::by_id(id)
        .get_results_async(&pool)
        .map_err(ImlApiError::ImlDieselAsyncError)
        .await?;

    let cmd = cmd.pop().unwrap();

    let jobs: Vec<ChromaCoreJob> = get_jobs_by_cmd(id, &pool)
        .map_err(ImlApiError::ImlDieselAsyncError)
        .await?;

    let steps: Vec<ChromaCoreStepresult> = ChromaCoreStepresult::by_jobs(jobs.iter().map(|j| j.id))
        .get_results_async(&pool)
        .map_err(ImlApiError::ImlDieselAsyncError)
        .await?;

    Ok(Command {
        cancelled: cmd.cancelled,
        complete: cmd.complete,
        created_at: format!("{}", cmd.created_at),
        errored: cmd.errored,
        id: cmd.id as u32,
        message: cmd.message,
        resource_uri: format!("/api/{}/{}/", Command::endpoint_name(), cmd.id),
        jobs: jobs
            .iter()
            .map(|j| format!("/api/{}/{}/", TestHostJob::endpoint_name(), j.id))
            .collect(),
        logs: steps.iter().map(|s| s.log.clone()).join("\n"),
    })
}
