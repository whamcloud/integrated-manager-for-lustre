// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::ImlAgentError, cmd::cmd_output_success, http_comms::mailbox_client};
use futures::{future, stream, Future, IntoFuture, Stream as _};
use iml_fs::{read_file_to_end, stream_dir_lines, write_tempfile};
use std::{convert::Into, path::PathBuf};
use uuid::Uuid;

/// The device that is scanned for matching rules.
#[derive(Debug, Eq, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct StratagemDevice {
    pub path: String,
    pub groups: Vec<String>,
}

/// A list of rules + a name for the group of rules.
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

/// A rule to match over.
#[derive(Debug, Eq, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct StratagemRule {
    pub action: String,
    pub expression: String,
    pub argument: String,
    pub counter_name: Option<String>,
}

/// The top-level config
#[derive(Debug, Eq, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct StratagemConfig {
    pub flist_type: String,
    pub summarize_size: bool,
    pub groups: Vec<StratagemGroup>,
    pub device: StratagemDevice,
}

impl StratagemConfig {
    pub fn get_group_by_name(&self, name: &str) -> Option<&StratagemGroup> {
        self.groups.iter().find(|g| g.name == name)
    }
}

/// Contains matching results.
#[derive(Debug, serde::Serialize, serde::Deserialize)]
pub struct StratagemCounter {
    pub name: String,
    pub count: u64,
    pub size: u64,
    pub blocks: u64,
    pub flist_type: String,
}

/// A result for a `LAT_ATTR_CLASSIFY` rule.
#[derive(Debug, serde::Serialize, serde::Deserialize)]
pub struct StratagemClassifyResult {
    pub attr_type: String,
    pub flist_type: String,
    pub counters: Vec<StratagemCounter>,
}

/// A nested Counter used for matches to `LAT_ATTR_CLASSIFY`.
/// This is nested within `StratagemClassifyResult` and considerably
/// complicates the type hierarchy.
#[derive(Debug, serde::Serialize, serde::Deserialize)]
pub struct StratagemClassifyCounter {
    pub name: String,
    pub count: u64,
    pub size: u64,
    pub blocks: u64,
    pub flist_type: String,
    pub expression: String,
    pub classify: StratagemClassifyResult,
}

/// A result for a given rule group.
#[derive(Debug, serde::Serialize, serde::Deserialize)]
pub struct StratagemGroupResult {
    pub name: String,
    pub counters: Vec<StratagemCounters>,
}

/// Possible counter results.
/// `StratagemClassifyCounter` matches `LAT_ATTR_CLASSIFY`.
/// `StratagemCounter` matches everything else.
#[derive(Debug, serde::Serialize, serde::Deserialize)]
#[serde(untagged)]
pub enum StratagemCounters {
    StratagemClassifyCounter(StratagemClassifyCounter),
    StratagemCounter(StratagemCounter),
}

#[derive(Debug, serde::Serialize, serde::Deserialize)]
pub struct StratagemResult {
    pub group_counters: Vec<StratagemGroupResult>,
}

/// Abstracts over the fact that `StratagemClassifyCounter`
/// and `StratagemCounter` are mostly the same.
///
/// Exposes their common properties as trait methods.
pub trait Counter {
    fn name(&self) -> &str;
    fn count(&self) -> u64;
    fn size(&self) -> u64;
    fn have_flist(&self) -> bool;
}

impl Counter for &StratagemCounter {
    fn name(&self) -> &str {
        &self.name
    }
    fn count(&self) -> u64 {
        self.count
    }
    fn size(&self) -> u64 {
        self.size
    }
    fn have_flist(&self) -> bool {
        self.flist_type != "none"
    }
}

impl Counter for &StratagemClassifyCounter {
    fn name(&self) -> &str {
        &self.name
    }
    fn count(&self) -> u64 {
        self.count
    }
    fn size(&self) -> u64 {
        self.size
    }
    fn have_flist(&self) -> bool {
        self.flist_type != "none"
    }
}

impl Counter for &StratagemCounters {
    fn have_flist(&self) -> bool {
        match self {
            StratagemCounters::StratagemCounter(StratagemCounter { flist_type, .. })
            | StratagemCounters::StratagemClassifyCounter(StratagemClassifyCounter {
                flist_type,
                ..
            }) => flist_type != "none",
        }
    }
    fn name(&self) -> &str {
        match self {
            StratagemCounters::StratagemCounter(StratagemCounter { name, .. })
            | StratagemCounters::StratagemClassifyCounter(StratagemClassifyCounter {
                name, ..
            }) => name,
        }
    }
    fn count(&self) -> u64 {
        match self {
            StratagemCounters::StratagemCounter(StratagemCounter { count, .. })
            | StratagemCounters::StratagemClassifyCounter(StratagemClassifyCounter {
                count, ..
            }) => *count,
        }
    }
    fn size(&self) -> u64 {
        match self {
            StratagemCounters::StratagemCounter(StratagemCounter { size, .. })
            | StratagemCounters::StratagemClassifyCounter(StratagemClassifyCounter {
                size, ..
            }) => *size,
        }
    }
}

/// Pre-cooked config. This is a V1
/// thing, Future versions will expand to
/// expose the whole config to the user.
pub fn generate_cooked_config(path: String, rd: Option<u64>, pd: Option<u64>) -> StratagemConfig {
    let mut conf = StratagemConfig {
        flist_type: "none".into(),
        summarize_size: true,
        device: StratagemDevice {
            path,
            groups: vec!["size_distribution".into(), "user_distribution".into()],
        },
        groups: vec![
            StratagemGroup {
                rules: vec![
                    StratagemRule {
                        action: "LAT_COUNTER_INC".into(),
                        expression: "&& < size 1048576 != type S_IFDIR".into(),
                        argument: "SIZE_<_1M".into(),
                        counter_name: None,
                    },
                    StratagemRule {
                        action: "LAT_COUNTER_INC".into(),
                        expression: "&& >= size 1048576000000 != type S_IFDIR".into(),
                        argument: "SIZE_>=_1T".into(),
                        counter_name: None,
                    },
                    StratagemRule {
                        action: "LAT_COUNTER_INC".into(),
                        expression: "&& >= size 1048576000 != type S_IFDIR".into(),
                        argument: "SIZE_>=_1G".into(),
                        counter_name: None,
                    },
                    StratagemRule {
                        action: "LAT_COUNTER_INC".into(),
                        expression: "&& >= size 1048576 != type S_IFDIR".into(),
                        argument: "1M_<=_SIZE_<_1G".into(),
                        counter_name: None,
                    },
                ],
                name: "size_distribution".into(),
            },
            StratagemGroup {
                rules: vec![StratagemRule {
                    action: "LAT_ATTR_CLASSIFY".into(),
                    expression: "!= type S_IFDIR".into(),
                    argument: "uid".into(),
                    counter_name: Some("top_inode_users".into()),
                }],
                name: "user_distribution".into(),
            },
        ],
    };

    if let Some(pd) = pd {
        let name = "purge_fids";

        conf.device.groups.push(name.into());

        conf.groups.push(StratagemGroup {
            name: name.into(),
            rules: vec![StratagemRule {
                action: "LAT_SHELL_CMD_FID".into(),
                expression: format!("&& != type S_IFDIR < atime - sys_time {}", pd),
                argument: "fids_expired".into(),
                counter_name: Some("fids_expired".into()),
            }],
        });
    }

    if let Some(rd) = rd {
        let name = "warn_fids";

        conf.device.groups.push(name.into());

        let expression = if let Some(pd) = pd {
            format!(
                "&& != type S_IFDIR && < atime - sys_time {} > atime - sys_time {}",
                rd, pd
            )
        } else {
            format!("&& != type S_IFDIR < atime - sys_time {}", rd)
        };

        conf.groups.push(StratagemGroup {
            name: name.into(),
            rules: vec![StratagemRule {
                action: "LAT_SHELL_CMD_FID".into(),
                expression,
                argument: "fids_expiring_soon".into(),
                counter_name: Some("fids_expiring_soon".into()),
            }],
        });
    }

    conf
}

type MailboxFiles = Vec<(PathBuf, String)>;

/// Given a results.json
/// Returns all the directories that contain fid files.
pub fn get_mailbox_files(
    base_dir: &str,
    stratagem_data: &StratagemConfig,
    stratagem_result: &StratagemResult,
) -> MailboxFiles {
    stratagem_result
        .group_counters
        .iter()
        .filter(|x| x.counters.iter().any(|x| Counter::have_flist(&x)))
        .map(|group| {
            group
                .counters
                .iter()
                .enumerate()
                .filter(|(_, x)| Counter::have_flist(x))
                .map(move |(idx, counter)| {
                    let group = stratagem_data
                        .get_group_by_name(&group.name)
                        .unwrap_or_else(|| panic!("did not find group by name {}", group.name));

                    let rule = group
                        .get_rule_by_idx(idx - 1)
                        .unwrap_or_else(|| panic!("did not find rule by idx {}", idx - 1));

                    let p = [base_dir, &group.name, &counter.name()]
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
/// This will only trigger a scan and return a triple of `(String, StratagemResult, MailboxFiles)`
///
/// It will *not* stream data for processing
pub fn trigger_scan(
    data: StratagemConfig,
) -> impl Future<Item = (String, StratagemResult, MailboxFiles), Error = ImlAgentError> {
    let id = Uuid::new_v4().to_hyphenated().to_string();

    let tmp_dir = format!("/tmp/{}/", id);
    let tmp_dir2 = tmp_dir.clone();

    let result_file = format!("{}result.json", tmp_dir);

    serde_json::to_vec(&data)
        .into_future()
        .from_err()
        .and_then(|x| write_tempfile(x).from_err())
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
        .and_then(move |_| read_file_to_end(result_file).from_err())
        .and_then(|xs| serde_json::from_slice(&xs).map_err(Into::into))
        .map(move |x| {
            let mailbox_files = get_mailbox_files(&tmp_dir2, &data, &x);
            (tmp_dir2, x, mailbox_files)
        })
}

/// Streams output for all given mailbox files
///
/// This fn will stream all files in parallel and return once they have all finished.
pub fn stream_fidlists(
    mailbox_files: MailboxFiles,
) -> impl Future<Item = (), Error = ImlAgentError> {
    let mailbox_files = mailbox_files.into_iter().map(|(file, address)| {
        stream_dir_lines(file)
            .from_err()
            .chunks(5000)
            .for_each(move |xs| {
                mailbox_client::send(
                    address.clone(),
                    stream::iter_ok(xs.into_iter().map(|x| format!("{}\n", x)).map(|x| x.into())),
                )
            })
    });

    future::join_all(mailbox_files).map(|_| ())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_get_fid_dirs() {
        let stratagem_data = StratagemConfig {
            flist_type: "none".into(),
            summarize_size: true,
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
                            argument: "SIZE_<_1M".into(),
                            counter_name: None,
                        },
                        StratagemRule {
                            action: "LAT_COUNTER_INC".into(),
                            expression: "&& >= size 1048576 < size 1048576000".into(),
                            argument: "1M_<=_SIZE_<_1G".into(),
                            counter_name: None,
                        },
                        StratagemRule {
                            action: "LAT_COUNTER_INC".into(),
                            expression: ">= size 1048576000".into(),
                            argument: "SIZE_>=_1G".into(),
                            counter_name: None,
                        },
                        StratagemRule {
                            action: "LAT_COUNTER_INC".into(),
                            expression: ">= size 1048576000000".into(),
                            argument: "SIZE_>=_1T".into(),
                            counter_name: None,
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
                            counter_name: Some("fids_expiring_soon".into()),
                        },
                        StratagemRule {
                            action: "LAT_SHELL_CMD_FID".into(),
                            expression: "< atime - sys_time 5184000000".into(),
                            argument: "fids_expired".into(),
                            counter_name: Some("fids_expired".into()),
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
                        StratagemCounters::StratagemCounter(StratagemCounter {
                            count: 1,
                            blocks: 0,
                            size: 0,
                            flist_type: "none".into(),
                            name: "Other".into(),
                        }),
                        StratagemCounters::StratagemCounter(StratagemCounter {
                            count: 0,
                            blocks: 0,
                            size: 0,
                            flist_type: "none".into(),
                            name: "smaller_than_1M".into(),
                        }),
                        StratagemCounters::StratagemCounter(StratagemCounter {
                            count: 0,
                            blocks: 0,
                            size: 0,
                            flist_type: "none".into(),
                            name: "not_smaller_than_1M_and_smaller_than_1G".into(),
                        }),
                        StratagemCounters::StratagemCounter(StratagemCounter {
                            count: 1,
                            blocks: 0,
                            size: 0,
                            flist_type: "none".into(),
                            name: "not_smaller_than_1G".into(),
                        }),
                        StratagemCounters::StratagemCounter(StratagemCounter {
                            count: 0,
                            blocks: 0,
                            size: 0,
                            flist_type: "none".into(),
                            name: "not_smaller_than_1T".into(),
                        }),
                    ],
                },
                StratagemGroupResult {
                    name: "warn_purge_times".into(),
                    counters: vec![
                        StratagemCounters::StratagemCounter(StratagemCounter {
                            count: 2,
                            blocks: 0,
                            size: 0,
                            flist_type: "none".into(),
                            name: "Other".into(),
                        }),
                        StratagemCounters::StratagemCounter(StratagemCounter {
                            count: 0,
                            blocks: 0,
                            size: 0,
                            flist_type: "fid".into(),
                            name: "shell_cmd_of_rule_0".into(),
                        }),
                        StratagemCounters::StratagemCounter(StratagemCounter {
                            count: 0,
                            blocks: 0,
                            size: 0,
                            flist_type: "fid".into(),
                            name: "shell_cmd_of_rule_1".into(),
                        }),
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
