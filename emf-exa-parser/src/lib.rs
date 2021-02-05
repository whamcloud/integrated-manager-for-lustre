// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

mod exaparser;

pub use crate::exaparser::exascaler_configuration::ExascalerConfiguration;
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
    path: &str,
) -> Result<ExascalerConfiguration, EXAParserError> {
    let python_code = include_str!("extract_exa_json.py");
    let output = Command::new("python")
        .arg("-c")
        .arg(&python_code)
        .arg(path)
        .checked_output()
        .await?;
    let output_str = String::from_utf8(output.stdout)?;
    if output.status.success() {
        serde_json::from_str(&output_str).map_err(|e| EXAParserError::JsonError(e))
    } else {
        let err = String::from_utf8(output.stderr)?;
        Err(EXAParserError::PythonError { err })
    }
}
