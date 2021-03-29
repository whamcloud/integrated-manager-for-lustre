// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub mod alert;
pub mod api;
pub mod api_utils;
pub mod command;
pub mod command_utils;
pub mod config_utils;
pub mod display_utils;
pub mod error;
pub mod filesystem;
pub mod grafana;
pub mod host;
pub mod influx;
pub mod kuma;
pub mod nginx;
pub mod ostpool;
pub mod postgres;
pub mod run;
pub mod snapshot;
pub mod stratagem;
pub mod target;

use std::env;

fn exe_name() -> Option<String> {
    Some(
        std::env::current_exe()
            .ok()?
            .file_stem()?
            .to_str()?
            .to_string(),
    )
}

pub fn selfname(suffix: Option<&str>) -> Option<String> {
    match env::var("CLI_NAME") {
        Ok(n) => suffix.map(|s| format!("{}-{}", n, s)).or(Some(n)),
        Err(_) => exe_name(),
    }
}
