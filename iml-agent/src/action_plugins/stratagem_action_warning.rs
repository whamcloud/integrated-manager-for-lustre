// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use csv;
use libc;
use std::ffi::CStr;
use std::io;
use crate::agent_error::ImlAgentError;
           
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

pub fn write_records(
    device: &String,
    args: impl IntoIterator<Item = String>,
    out: impl io::Write,
) -> Result<(), ImlAgentError> {
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


