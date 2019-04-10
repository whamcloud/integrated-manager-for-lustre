// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

// Usage: stratagem_purge FS [NID1] [NID2] ...

use std::process::exit;
use structopt::StructOpt;
mod cli;

#[derive(Debug, StructOpt)]
#[structopt(name = "stratagem_purge")]
struct Opt {
    #[structopt(short = "i")]
    /// File to read from, "-" for stdin
    input: Option<String>,

    #[structopt(name = "FSNAME")]
    /// Lustre filesystem name, or mountpoint
    fsname: String,

    #[structopt(name = "FIDS")]
    /// Optional list of FIDs to purge
    fidlist: Vec<String>,
}

fn main() {
    env_logger::init();
    let opt = Opt::from_args();
    let device = opt.fsname;
    let input = cli::input_to_iter(opt.input, opt.fidlist);

    if liblustreapi::rmfid(&device, input).is_err() {
        exit(-1);
    }
}
