// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    agent_error::ImlAgentError,
    cmd::cmd_output_success,
    fs::{read_file_to_end, write_tempfile},
};
use futures::prelude::{Future, IntoFuture};
use std::{collections::HashMap, convert::Into, path::PathBuf};
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

impl StratagemGroup {
    pub fn get_rule_by_idx(&self, idx: usize) -> Option<&StratagemRule> {
        self.rules.get(idx)
    }
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

impl StratagemData {
    pub fn get_group_by_name(&self, name: &str) -> Option<&StratagemGroup> {
        self.groups.iter().find(|g| g.name == name)
    }
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

impl HaveFlist for &StratagemCounter {
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

type MailboxFiles = Vec<(PathBuf, String)>;

/// Given a results.json
/// Returns all the directories that contain fid files.
pub fn get_mailbox_files(
    base_dir: &str,
    stratagem_data: &StratagemData,
    stratagen_result: &StratagemResult,
) -> MailboxFiles {
    stratagen_result
        .group_counters
        .iter()
        .filter(|x| has_flists(&x.counters))
        .map(|group| {
            group
                .counters
                .iter()
                .enumerate()
                .filter(|(_, x)| HaveFlist::have_flist(x))
                .map(move |(idx, counter)| {
                    let group = stratagem_data
                        .get_group_by_name(&group.name)
                        .expect("did not find group by name");

                    let rule = group
                        .get_rule_by_idx(idx - 1)
                        .expect("did not find rule by idx");

                    let p = [base_dir, &group.name, &counter.name]
                        .iter()
                        .cloned()
                        .collect::<PathBuf>();

                    (p, format!("{}-{}", group.name, rule.argument))
                })
        })
        .flatten()
        .collect()
}

/// Triggers a scan with Stratagem.
/// This will only trigger a scan and return a triple of `(StratagemResult, String, MailboxFiles)`
///
/// It will *not* stream data for processing
pub fn trigger_scan(
    data: StratagemData,
) -> impl Future<Item = (StratagemResult, String, MailboxFiles), Error = ImlAgentError> {
    let id = Uuid::new_v4().to_hyphenated().to_string();

    let tmp_dir = format!("/tmp/{}/", id);
    let tmp_dir2 = tmp_dir.clone();

    let result_file = format!("{}result.json", tmp_dir);

    serde_json::to_vec(&data)
        .into_future()
        .from_err()
        .and_then(write_tempfile)
        .and_then(move |f| {
            cmd_output_success(
                "/usr/bin/lipe_scan",
                &[
                    "-c",
                    &f.path().to_str().unwrap(),
                    "-W",
                    &format!("/tmp/{}", id),
                ],
            )
            .map(|x| (x, f))
        })
        .map(|(output, _f)| String::from_utf8_lossy(&output.stdout).into_owned())
        .and_then(move |_| read_file_to_end(result_file))
        .and_then(|xs| serde_json::from_slice(&xs).map_err(Into::into))
        .map(move |x| {
            let mailbox_files = get_mailbox_files(&tmp_dir2, &data, &x);
            (x, tmp_dir2, mailbox_files)
        })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_get_fid_dirs() {
        let stratagem_data = StratagemData {
            dump_flist: false,
            device: StratagemDevice {
                path: "/dev/mapper/mpathb".into(),
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
        };

        let stratagem_result = StratagemResult {
            group_counters: vec![
                StratagemGroupResult {
                    name: "size_distribution".into(),
                    counters: vec![
                        StratagemCounter {
                            count: 1,
                            have_flist: false,
                            name: "Other".into(),
                            extra: HashMap::new(),
                        },
                        StratagemCounter {
                            count: 0,
                            have_flist: false,
                            name: "smaller_than_1M".into(),
                            extra: HashMap::new(),
                        },
                        StratagemCounter {
                            count: 0,
                            have_flist: false,
                            name: "not_smaller_than_1M_and_smaller_than_1G".into(),
                            extra: HashMap::new(),
                        },
                        StratagemCounter {
                            count: 1,
                            have_flist: false,
                            name: "not_smaller_than_1G".into(),
                            extra: HashMap::new(),
                        },
                        StratagemCounter {
                            count: 0,
                            have_flist: false,
                            name: "not_smaller_than_1T".into(),
                            extra: HashMap::new(),
                        },
                    ],
                },
                StratagemGroupResult {
                    name: "warn_purge_times".into(),
                    counters: vec![
                        StratagemCounter {
                            count: 2,
                            have_flist: false,
                            name: "Other".into(),
                            extra: HashMap::new(),
                        },
                        StratagemCounter {
                            count: 0,
                            have_flist: true,
                            name: "shell_cmd_of_rule_0".into(),
                            extra: HashMap::new(),
                        },
                        StratagemCounter {
                            count: 0,
                            have_flist: true,
                            name: "shell_cmd_of_rule_1".into(),
                            extra: HashMap::new(),
                        },
                    ],
                },
            ],
        };

        let actual = get_mailbox_files("foo_bar", &stratagem_data, &stratagem_result);

        assert_eq!(
            actual,
            vec![
                (
                    PathBuf::from("foo_bar/warn_purge_times/shell_cmd_of_rule_0"),
                    "warn_purge_times-fids_expiring_soon".into()
                ),
                (
                    PathBuf::from("foo_bar/warn_purge_times/shell_cmd_of_rule_1"),
                    "warn_purge_times-fids_expired".into()
                )
            ]
        );
    }
}
