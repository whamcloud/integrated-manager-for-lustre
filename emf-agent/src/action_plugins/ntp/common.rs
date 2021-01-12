// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::agent_error::EmfAgentError;
use futures::{Stream, TryStreamExt};
use std::path::Path;

pub static NTP_CONFIG_FILE: &str = "/etc/ntp.conf";
pub static MARKER: &str = "# EMF_EDIT";
pub static REMOVE_MARKER: &str = "#REMOVE_MARKER#";
pub static PREFIX: &str = "server";

/// Gets a stream to the ntp config
pub fn get_ntp_config_stream() -> impl Stream<Item = Result<String, EmfAgentError>> {
    emf_fs::stream_file_lines(Path::new(NTP_CONFIG_FILE)).err_into()
}
