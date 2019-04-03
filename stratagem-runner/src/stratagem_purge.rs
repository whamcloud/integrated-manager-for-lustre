// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

// Usage: stratagem_purge FS [NID1] [NID2] ...

use std::env;

fn main() {
    let mut args = env::args();
    let device = args.nth(1).expect("No device specified");

    liblustreapi::rmfid(&device, args).expect("Failed to remove all fids")
}
