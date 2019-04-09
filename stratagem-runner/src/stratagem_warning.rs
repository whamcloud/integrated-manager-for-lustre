// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

// Usage: stratagem_warning [FS-NAME|FS-MOUNT-POINT] [NID1] [NID2] ...

use libc;
use std::ffi::CStr;
use std::fs::File;
use std::io;
use std::io::prelude::*;
use std::io::BufReader;
use std::process::exit;
use stratagem_runner::error::StratagemError;
use structopt::StructOpt;

#[derive(Debug, StructOpt)]
#[structopt(name = "stratagem_warning")]
struct Opt {
    #[structopt(short = "i")]
    /// File to read from, "-" for stdin, or unspecified for on cli
    input: Option<String>,

    #[structopt(short = "o")]
    /// File to write to, or "-" or unspecified for stdout
    output: Option<String>,

    #[structopt(name = "FSNAME")]
    /// Lustre filesystem name, or mountpoint
    fsname: String,

    #[structopt(name = "FIDS")]
    /// Optional list of FIDs to purge
    fidlist: Vec<String>,
}

#[derive(Debug, serde::Serialize)]
#[serde(rename_all = "SCREAMING-KEBAB-CASE")]
struct Record<'a> {
    path: &'a str,
    user: &'a str,
    uid: u32,
    gid: u32,
    atime: i64,
    mtime: i64,
    ctime: i64,
    fid: &'a str,
}

fn write_records(
    device: &str,
    args: impl IntoIterator<Item = String>,
    out: impl io::Write,
) -> Result<(), StratagemError> {
    let mntpt = liblustreapi::search_rootpath(&device).map_err(|e| {
        log::error!("Failed to find rootpath({}) -> {:?}", device, e);
        e
    })?;

    let mut wtr = csv::Writer::from_writer(out);

    for fid in args {
        let path = match liblustreapi::fid2path(&device, &fid) {
            Ok(p) => p,
            Err(e) => {
                log::error!("Failed to fid2path: {}: {}", fid, e);
                continue;
            }
        };

        let pb: std::path::PathBuf = [&mntpt, &path].iter().collect();
        let fullpath = pb.to_str().unwrap();
        let stat = liblustreapi::mdc_stat(&fullpath).map_err(|e| {
            log::error!("Failed to mdc_stat({}) => {:?}", fullpath, e);
            e
        })?;
        let user = unsafe {
            let pwent = libc::getpwuid(stat.st_uid);
            if pwent.is_null() {
                log::error!("Failed to getpwuid({})", stat.st_uid);

                return Err(io::Error::from(io::ErrorKind::NotFound).into());
            }
            CStr::from_ptr((*pwent).pw_name).to_str()?
        };
        wtr.serialize(Record {
            path: &path,
            user: &user,
            uid: stat.st_uid,
            gid: stat.st_gid,
            atime: stat.st_atime,
            mtime: stat.st_mtime,
            ctime: stat.st_ctime,
            fid: &fid,
        })?;
    }

    wtr.flush()?;

    Ok(())
}

fn main() {
    env_logger::init();
    let opt = Opt::from_args();
    let device = opt.fsname;
    let output: Box<io::Write> = match opt.output {
        Some(file) => Box::new(File::create(file).unwrap()),
        None => Box::new(io::stdout()),
    };

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
    if let Err(_) = write_records(&device, input, output) {
        exit(-1);
    }
}
