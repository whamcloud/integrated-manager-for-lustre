// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{api_utils::graphql, display_utils::wrap_fut, error::EmfManagerCliError};
use emf_graphql_queries::state_machine as state_machine_queries;
use std::path::PathBuf;
use tokio::fs;

pub async fn cli(path: PathBuf) -> Result<(), EmfManagerCliError> {
    if !emf_fs::file_exists(&path).await {
        return Err(EmfManagerCliError::DoesNotExist(format!(
            "Input document at {} does not exist.",
            path.to_string_lossy()
        )));
    }

    let file = fs::read_to_string(&path).await?;

    let query = state_machine_queries::input_document::build(file);

    let resp: emf_graphql_queries::Response<state_machine_queries::input_document::Resp> =
        wrap_fut("Submitting Input...", graphql(query)).await?;

    tracing::debug!(?resp);

    Ok(())
}
