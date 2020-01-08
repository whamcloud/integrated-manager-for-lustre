// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use serde::Serialize;
use warp::{self, http::StatusCode, reject, Rejection, Reply};

#[derive(Debug)]
pub enum TimerError {
    WriteFailed,
    DeleteFailed,
    DaemonReloadFailed,
    EnableTimerError,
    DisableTimerError,
}

impl reject::Reject for TimerError {}

#[derive(Serialize)]
struct ErrorMessage<'a> {
    code: u16,
    message: &'a str,
}

pub async fn customize_error(err: Rejection) -> Result<impl Reply, Rejection> {
    if let Some(err) = err.find::<TimerError>() {
        let (code, msg) = match err {
            TimerError::WriteFailed => {
                tracing::error!("Failed to write config files!");
                (StatusCode::INTERNAL_SERVER_ERROR, "Writing config failed!")
            }
            TimerError::DeleteFailed => {
                tracing::error!("Failed to delete config files!");
                (StatusCode::INTERNAL_SERVER_ERROR, "Deleting config failed!")
            }
            TimerError::DaemonReloadFailed => {
                tracing::error!("Failed to reload the daemon!");
                (
                    StatusCode::INTERNAL_SERVER_ERROR,
                    "Daemon reload failed to spawn!",
                )
            }
            TimerError::EnableTimerError => {
                tracing::error!("Failed to enable timer!");
                (StatusCode::INTERNAL_SERVER_ERROR, "Failed to enable timer!")
            }
            TimerError::DisableTimerError => {
                tracing::error!("Failed to disable timer!");
                (
                    StatusCode::INTERNAL_SERVER_ERROR,
                    "Failed to disable timer!",
                )
            }
        };

        let json = warp::reply::json(&ErrorMessage {
            code: code.as_u16(),
            message: msg,
        });
        Ok(warp::reply::with_status(json, code))
    } else if let Some(_) = err.find::<warp::reject::MethodNotAllowed>() {
        let code = StatusCode::METHOD_NOT_ALLOWED;
        let json = warp::reply::json(&ErrorMessage {
            code: code.as_u16(),
            message: "oops, you aren't allowed to use this method.".into(),
        });
        Ok(warp::reply::with_status(json, code))
    } else {
        // Could be a NOT_FOUND, or any other internal error... here we just
        // let warp use its default rendering.
        Err(err)
    }
}
