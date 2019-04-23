// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::ImlAgentError, fs::write_tempfile};
use futures::prelude::*;
use serde;
use serde_json;
use std::process::Command;
use tokio_process::CommandExt;

#[derive(Debug, Eq, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct Devices {
    pub path: String,
    pub host_id: String,
    pub groups: Vec<String>,
    pub device_id: String,
}

#[derive(Debug, Eq, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct Groups {
    pub rules: Vec<Rules>,
    pub name: String,
}

#[derive(Debug, Eq, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct Rules {
    pub action: String,
    pub expression: String,
    pub argument: String,
}

#[derive(Debug, Eq, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct StratagemData {
    pub dump_flist: bool,
    pub groups: Vec<Groups>,
    pub devices: Vec<Devices>,
}

pub fn start_scan_stratagem(
    data: StratagemData,
) -> impl Future<Item = Vec<u8>, Error = ImlAgentError> {
    serde_json::to_vec(&data)
        .map_err(|e| e.into())
        .into_future()
        .and_then(write_tempfile)
        .and_then(|f| {
            Command::new("lipe")
                .args(&["-c", f.path().to_str().unwrap()])
                .output_async()
                .map_err(|e| e.into())
                .map(|output| output.stdout)
        })
}
