// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

extern crate futures;
extern crate tokio;

use crate::agent_error::{ImlAgentError, RequiredError};
use crate::lustre::search_rootpath;
use iml_wire_types::{FidError, FidItem};
use liblustreapi::LlapiFid;
use tokio::process::Command;
use tracing::error;

fn get_unique(input: &str) -> String {
    let mut output = String::new();
    for c in input.chars() {
        match c {
            '/' => output.push_str("_"),
            _ => output.push(c),
        }
    }
    output
}

async fn archive_fids(
    llapi: LlapiFid,
    target_name: &String,
    fid_list: Vec<FidItem>,
) -> Result<Vec<FidError>, ImlAgentError> {
    let mut result = Vec::new();

    for fid in fid_list {
        let fid_path = llapi.fid2path(&fid.fid)?;
        let src_file = format!("{}/{}\n", llapi.mntpt(), &fid_path);

        let output = Command::new("stgm_cloudsync")
            .arg("push")
            .arg(src_file)
            .arg(format!("{}:{}", target_name, get_unique(&fid_path)))
            .output();
        let output = output.await?;

        let res = FidError {
            fid: fid.fid.clone(),
            data: fid.data.clone(),
            errno: output.status.code().unwrap_or(0) as i16,
        };
        result.push(res);

        error!(
            "exited with {} {} {}",
            output.status,
            std::str::from_utf8(&output.stdout)?,
            std::str::from_utf8(&output.stderr)?
        );
    }

    Ok(result)
}

async fn restore_fids(
    llapi: LlapiFid,
    target_name: &String,
    fid_list: Vec<FidItem>,
) -> Result<Vec<FidError>, ImlAgentError> {
    let mut result = Vec::new();

    for fid in fid_list {
        let fid_path = llapi.fid2path(&fid.fid)?;
        let src_file = format!("{}/{}\n", llapi.mntpt(), &fid_path);

        let output = Command::new("stgm_cloudsync")
            .arg("pull")
            .arg(format!("{}:{}", target_name, get_unique(&fid_path)))
            .arg(src_file)
            .output();
        let output = output.await?;

        let res = FidError {
            fid: fid.fid.clone(),
            data: fid.data.clone(),
            errno: output.status.code().unwrap_or(0) as i16,
        };
        result.push(res);

        error!(
            "exited with {} {} {}",
            output.status,
            std::str::from_utf8(&output.stdout)?,
            std::str::from_utf8(&output.stderr)?
        );
    }
    Ok(result)
}

/// Process FIDs
pub async fn process_fids(
    (fsname_or_mntpath, task_args, fid_list): (
        std::string::String,
        std::collections::HashMap<std::string::String, std::string::String>,
        std::vec::Vec<iml_wire_types::FidItem>,
    ),
) -> Result<Vec<FidError>, ImlAgentError> {
    let llapi = search_rootpath(fsname_or_mntpath).await?;

    let target_name = task_args
        .get("remote".into())
        .ok_or(RequiredError("Task missing 'remote' argument".to_string()))?;

    let action_name = task_args
        .get("action".into())
        .ok_or(RequiredError("Task missing 'action' argument".to_string()))?;

    // fuck it, panic.  I can'd figure out how to return an error from a match
    // statement, but I can above.
    match action_name.as_str() {
        "push" => archive_fids(llapi.clone(), target_name, fid_list).await,
        "pull" => restore_fids(llapi.clone(), target_name, fid_list).await,
        _ => panic!(),
    }
}
