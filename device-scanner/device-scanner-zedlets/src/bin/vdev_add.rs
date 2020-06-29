// Copyright (c) 2018 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use device_scanner_zedlets::{send_data, zpool, Result};
use device_types::zed::ZedCommand;

fn main() -> Result<()> {
    let x = ZedCommand::AddVdev(zpool::get_name()?, zpool::get_guid()?);

    send_data(x)
}
