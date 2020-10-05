// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use std::collections::BTreeSet;
pub mod api;
pub mod api_utils;
pub mod display_utils;
pub mod error;
pub mod filesystem;
pub mod nginx;
pub mod ostpool;
pub mod profile;
pub mod server;
pub mod snapshot;
pub mod stratagem;
pub mod update_repo_file;

pub fn parse_hosts(hosts: &[String]) -> Result<BTreeSet<String>, error::ImlManagerCliError> {
    let parsed: Vec<BTreeSet<String>> = hosts
        .iter()
        .map(|x| hostlist_parser::parse(x))
        .collect::<Result<_, _>>()?;

    let union = parsed
        .into_iter()
        .fold(BTreeSet::new(), |acc, h| acc.union(&h).cloned().collect());

    Ok(union)
}

pub fn selfname() -> Option<String> {
    Some(
        std::env::current_exe()
            .ok()?
            .file_stem()?
            .to_str()?
            .to_string(),
    )
}
