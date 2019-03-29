// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

// Usage: stratagem_purge FS [NID1] [NID2] ...

use liblustreapi;
use std::env;
use std::process;

fn main() {
    let mut args = env::args();
    let device = args.nth(1).expect("No device specified");
    // This is neccissary, but I don't know why yet.
    let _ = { std::io::stdout(); () };

    if let Err(e) = liblustreapi::rmfid(&device, args) {
        eprintln!("Failed to remove all fids {}", e);
        process::exit(1);
    }
}
