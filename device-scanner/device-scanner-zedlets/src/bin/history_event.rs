// Copyright (c) 2018 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use device_scanner_zedlets::{
    send_data,
    zed::{self, HistoryEvent},
    zfs, zpool, Result,
};
use device_types::zed::ZedCommand;

fn main() -> Result<()> {
    let history_name = zed::get_history_name()?;

    let guid = zpool::get_guid()?;

    let zfs_name = zfs::get_name();

    let x = match (history_name, zfs_name) {
        (HistoryEvent::Create, Ok(name)) => Some(ZedCommand::CreateZfs(guid, name)),
        (HistoryEvent::Destroy, Ok(name)) => Some(ZedCommand::DestroyZfs(guid, name)),
        (HistoryEvent::Set, Ok(name)) => {
            let (k, v) = zed::get_history_string()?;

            Some(ZedCommand::SetZfsProp(guid, name, k, v))
        }
        (HistoryEvent::Set, Err(_)) => {
            let (k, v) = zed::get_history_string()?;

            Some(ZedCommand::SetZpoolProp(guid, k, v))
        }
        _ => None,
    };

    if let Some(x) = x {
        send_data(x)?;
    }

    Ok(())
}
