// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use warp::reject;

#[derive(Debug)]
pub enum TimerError {
    IoError(std::io::Error),
}

impl reject::Reject for TimerError {}

#[derive(serde::Serialize)]
struct ErrorMessage<'a> {
    code: u16,
    message: &'a str,
}
