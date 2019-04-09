// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

// Usage: stratagem_purge FS [NID1] [NID2] ...

use std::fs::File;
use std::io;
use std::io::prelude::*;
use std::io::BufReader;
use std::process::exit;
use structopt::StructOpt;

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
    let input: Box<Iterator<Item = String>> = match opt.input {
        None => {
            if opt.fidlist.len() == 0 {
                Box::new(BufReader::new(io::stdin()).lines().map(|x| x.unwrap()))
            } else {
                Box::new(opt.fidlist.iter().map(|x| x.to_owned()))
            }
        }
        Some(name) => {
            let buf: Box<BufRead> = match name.as_ref() {
                "-" => Box::new(BufReader::new(io::stdin())),
                _ => {
                    let f = match File::open(&name) {
                        Ok(x) => x,
                        Err(e) => {
                            log::error!("Failed to open {}: {}", &name, e);
                            exit(-1);
                        }
                    };
                    Box::new(BufReader::new(f))
                }
            };
            Box::new(buf.lines().map(|x| x.unwrap()))
        }
    };

    if let Err(_) = liblustreapi::rmfid(&device, input) {
        exit(-1);
    }
}
