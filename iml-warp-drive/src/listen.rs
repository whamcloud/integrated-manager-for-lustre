// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{db_record, DbRecord, TableName};
use std::convert::TryFrom;

#[derive(serde::Deserialize, Debug)]
#[serde(rename_all = "UPPERCASE")]
pub enum MessageType {
    Update,
    Insert,
    Delete,
}

pub fn into_db_record(s: &str) -> serde_json::error::Result<(MessageType, DbRecord)> {
    let (msg_type, table_name, x): (MessageType, TableName, serde_json::Value) =
        serde_json::from_str(&s)?;

    let r = db_record::DbRecord::try_from((table_name, x))?;

    Ok((msg_type, r))
}
