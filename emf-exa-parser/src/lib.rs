// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub mod config;

use crate::config::ExascalerConfiguration;
use emf_cmd::{CheckedCommandExt, Command};
use std::io;
use std::string::FromUtf8Error;
use thiserror::Error;

#[derive(Error, Debug)]
pub enum EXAParserError {
    #[error("The command returned an invalid string")]
    UtfError(#[from] FromUtf8Error),

    #[error("Unable to launch command")]
    IoError(#[from] io::Error),

    #[error("Python error: {err:?}")]
    PythonError { err: String },

    #[error("Unable to launch command")]
    CmdError(#[from] emf_cmd::CmdError),

    #[error("Serde json error")]
    JsonError(#[from] serde_json::Error),
}

pub async fn parse_exascaler_conf_from_file(
    path: impl Into<Option<&str>>,
) -> Result<ExascalerConfiguration, EXAParserError> {
    let mut args = vec!["--api"];
    if let Some(cfg) = path.into() {
        args.push("--config-file");
        args.push(cfg);
    }

    let output = Command::new("es_config_show")
        .args(args)
        .checked_output()
        .await?;
    let output_str = String::from_utf8(output.stdout)?;
    if output.status.success() {
        serde_json::from_str(&output_str).map_err(EXAParserError::JsonError)
    } else {
        let err = String::from_utf8(output.stderr)?;
        Err(EXAParserError::PythonError { err })
    }
}
