// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    agent_error::ImlAgentError,
    cmd::cmd_output_success,
    fs::{read_file_to_end, stream_dirs, write_tempfile},
};
use futures::prelude::*;
use std::{collections::HashMap, convert::Into};
use uuid::Uuid;

#[derive(Debug, Eq, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct StratagemDevice {
    pub path: String,
    pub groups: Vec<String>,
}

#[derive(Debug, Eq, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct StratagemGroup {
    pub rules: Vec<StratagemRule>,
    pub name: String,
}

#[derive(Debug, Eq, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct StratagemRule {
    pub action: String,
    pub expression: String,
    pub argument: String,
}

#[derive(Debug, Eq, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct StratagemData {
    pub dump_flist: bool,
    pub groups: Vec<StratagemGroup>,
    pub device: StratagemDevice,
}

#[derive(Debug, serde::Serialize, serde::Deserialize)]
pub struct StratagemCounter {
    pub name: String,
    pub count: u64,
    pub have_flist: bool,
    #[serde(flatten)]
    pub extra: HashMap<String, serde_json::Value>,
}

#[derive(Debug, serde::Serialize, serde::Deserialize)]
pub struct StratagemGroupResult {
    pub name: String,
    pub counters: Vec<StratagemCounter>,
}

#[derive(Debug, serde::Serialize, serde::Deserialize)]
pub struct StratagemResult {
    pub group_counters: Vec<StratagemGroupResult>,
}

trait HaveFlist {
    fn have_flist(&self) -> bool;
}

impl HaveFlist for StratagemCounter {
    fn have_flist(&self) -> bool {
        self.have_flist
    }
}

/// Pre-cooked config. This is a V1
/// thing, Future versions will expand to
/// expose the whole config to the user.
pub fn generate_cooked_config(path: String) -> StratagemData {
    StratagemData {
        dump_flist: false,
        device: StratagemDevice {
            path,
            groups: vec!["size_distribution".into(), "warn_purge_times".into()],
        },
        groups: vec![
            StratagemGroup {
                rules: vec![
                    StratagemRule {
                        action: "LAT_COUNTER_INC".into(),
                        expression: "< size 1048576".into(),
                        argument: "smaller_than_1M".into(),
                    },
                    StratagemRule {
                        action: "LAT_COUNTER_INC".into(),
                        expression: "&& >= size 1048576 < size 1048576000".into(),
                        argument: "not_smaller_than_1M_and_smaller_than_1G".into(),
                    },
                    StratagemRule {
                        action: "LAT_COUNTER_INC".into(),
                        expression: ">= size 1048576000".into(),
                        argument: "not_smaller_than_1G".into(),
                    },
                    StratagemRule {
                        action: "LAT_COUNTER_INC".into(),
                        expression: ">= size 1048576000000".into(),
                        argument: "not_smaller_than_1T".into(),
                    },
                ],
                name: "size_distribution".into(),
            },
            StratagemGroup {
                rules: vec![
                    StratagemRule {
                        action: "LAT_SHELL_CMD_FID".into(),
                        expression: "< atime - sys_time 18000000".into(),
                        argument: "fids_expiring_soon".into(),
                    },
                    StratagemRule {
                        action: "LAT_SHELL_CMD_FID".into(),
                        expression: "< atime - sys_time 5184000000".into(),
                        argument: "fids_expired".into(),
                    },
                ],
                name: "warn_purge_times".into(),
            },
        ],
    }
}

fn has_flists<T: HaveFlist>(xs: &[T]) -> bool {
    xs.iter().any(HaveFlist::have_flist)
}

/// Given a results.json
/// Returns all the directories that contain fid files.
pub fn get_fid_dirs(results: &StratagemResult) -> Vec<String> {
    results
        .group_counters
        .iter()
        .filter(|x| has_flists(&x.counters))
        .map(|x| &x.counters)
        .flatten()
        .map(|x| x.name.clone())
        .collect()
}

/// Triggers a scan with Stratagem.
/// This will only trigger a scan and return `results.json`
///
/// It will *not* stream data for processing
pub fn trigger_scan(
    data: StratagemData,
) -> impl Future<Item = (StratagemResult, String), Error = ImlAgentError> {
    let id = Uuid::new_v4().to_hyphenated().to_string();
    let id2 = id.clone();
    let id3 = id.clone();

    serde_json::to_vec(&data)
        .into_future()
        .from_err()
        .and_then(write_tempfile)
        .and_then(move |f| {
            cmd_output_success("lipe_scan", &["-c", &f.path().to_str().unwrap(), "-W", &id])
                .map(|x| (x, f))
        })
        .map(|(output, _f)| String::from_utf8_lossy(&output.stdout).into_owned())
        .and_then(move |_| read_file_to_end(format!("/tmp/{}/result.json", id2)))
        .and_then(|xs| serde_json::from_slice(&xs).map_err(Into::into))
        .map(move |x| (x, format!("/tmp/{}/", id3)))
}

// pub fn start_scan_stratagem(
//     data: StratagemData,
// ) -> impl Future<Item = (StratagemResult, Vec<String>), Error = ImlAgentError> {
//     let id = Uuid::new_v4().to_hyphenated().to_string();
//     let id2 = id.clone();

//     serde_json::to_vec(&data)
//         .into_future()
//         .from_err()
//         .and_then(write_tempfile)
//         .and_then(move |f| {
//             cmd_output_success("lipe_scan", &["-c", &f.path().to_str().unwrap(), "-W", &id])
//                 .map(|x| (x, f))
//         })
//         .map(|(output, _f)| String::from_utf8_lossy(&output.stdout).into_owned())
//         .and_then(move |_| read_file_to_end(format!("/tmp/{}/result.json", id2)))
//         .and_then(|xs| serde_json::from_slice(&xs).map_err(Into::into))
//         .and_then(|x: StratagemResult| {
//             let dirs = get_fid_dirs(&x);

//             eprintln!("{:?}", dirs);

//             // stream_dirs(dirs).collect().map(move |xs| (x, xs))

//             Ok((x, vec![]))
//         })
// }
