// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::error::TimerError;
use tokio::process::Command;
use warp::{self, reject};

/// Takes a command, a value to be passed upon success, and the error type if
/// the command fails. A child is asynchronously spawned and if the command
/// completes successfully, the success value that is passed in will be returned.
/// If not successful, the timer_error will be returned.
pub async fn spawn_command<T>(
    cmd: &mut Command,
    success_val: T,
    timer_error: TimerError,
) -> Result<T, warp::Rejection> {
    let spawn_result = cmd.spawn();

    match spawn_result {
        Ok(child) => {
            let status = child.await;
            match status {
                Ok(exit_status) => {
                    if exit_status.success() {
                        Ok::<T, warp::Rejection>(success_val)
                    } else {
                        Err::<T, warp::Rejection>(reject::custom(timer_error))
                    }
                }
                Err(_) => Err::<T, warp::Rejection>(reject::custom(timer_error)),
            }
        }
        Err(_) => Err::<T, warp::Rejection>(reject::custom(timer_error)),
    }
}
