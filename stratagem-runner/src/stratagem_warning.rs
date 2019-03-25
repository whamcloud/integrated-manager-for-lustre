// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

// Usage: stratagem_warning FS [NID1] [NID2] ...

use llapi;
use std::env;

fn main() {
    let mut args = env::args();
    let device = args.nth(1).expect("No device specified");

    for fid in args {
        if let Some(path) = llapi::fid2path(&device, &fid) {
            println!("{}, {}", path, fid);
        }
    }
}
