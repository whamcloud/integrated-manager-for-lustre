// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::ImlAgentError, env, fidlist, http_comms::mailbox_client};
use csv;
use futures::sync::mpsc::channel;
use futures::{Future, Sink, Stream};
use libc;
use std::ffi::CStr;
use std::io;
use std::path::PathBuf;

#[derive(Debug, serde::Serialize)]
#[serde(rename_all = "SCREAMING-KEBAB-CASE")]
struct Record {
    path: String,
    user: String,
    uid: u32,
    gid: u32,
    atime: i64,
    mtime: i64,
    ctime: i64,
    fid: String,
}

fn fid2record(mntpt: &String, fli: &fidlist::FidListItem) -> Result<Record, ImlAgentError> {
    let path = match liblustreapi::fid2path(&mntpt, &fli.fid) {
        Ok(p) => p,
        Err(e) => {
            log::error!("Failed to fid2path: {}: {}", fli.fid, e);
            return Err(e.into());
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
    Ok(Record {
        path: path.to_string(),
        user: user.to_string(),
        uid: stat.st_uid,
        gid: stat.st_gid,
        atime: stat.st_atime,
        mtime: stat.st_mtime,
        ctime: stat.st_ctime,
        fid: fli.fid.to_string(),
    })
}

pub fn write_records(
    device: &str,
    args: impl IntoIterator<Item = String>,
    out: impl io::Write,
) -> Result<(), ImlAgentError> {
    let mntpt = liblustreapi::search_rootpath(&device).map_err(|e| {
        log::error!("Failed to find rootpath({}) -> {:?}", device, e);
        e
    })?;

    let mut wtr = csv::Writer::from_writer(out);

    for fid in args {
        let rec = match fid2record(&mntpt, &fidlist::FidListItem::new(fid)) {
            Ok(r) => r,
            Err(_) => continue,
        };
        wtr.serialize(rec)?;
    }

    wtr.flush()?;

    Ok(())
}

// Read mailbox and build a csv of files. return pathname of generated csv
//
pub fn read_mailbox(
    device: &str,
    mailbox: &str,
) -> impl Future<Item = String, Error = ImlAgentError> {
    let mntpt = match liblustreapi::search_rootpath(&device) {
        Ok(m) => m,
        Err(e) => {
            panic!("Failed to find rootpath({}) -> {:?}", device, e);
            //return futures::future::err(ImlAgentError::LiblustreError(e));
        }
    };

    let mbox = mailbox.to_string();

    let mut fpath = PathBuf::from(env::get_var_else("REPORT_DIR", "/tmp"));
    fpath.push(mailbox);
    fpath.set_extension("csv");
    let name = fpath.into_os_string().into_string().unwrap();

    let mut wtr = match csv::Writer::from_path(&name) {
        Ok(w) => w,
        Err(e) => {
            panic!("Failed open writer ({}) -> {:?}", name, e);
            //return futures::future::err(ImlAgentError::CsvError(e));
        }
    };
    let (sender, recv) = channel(4096);

    recv.for_each(move |rec: Record| {
        if let Err(err) = wtr.serialize(&rec) {
            log::error!("Failed to write record for fid {}: {}", rec.fid, err);
        }
        Ok(())
    })
    .join(
        mailbox_client::get(mbox)
            .and_then(|s| serde_json::from_str(&s).map_err(ImlAgentError::Serde))
            .and_then(move |fli: fidlist::FidListItem| fid2record(&mntpt, &fli))
            .map_err(|e| {
                log::error!("Failed {:?}", e);
                ()
            })
            .for_each(move |rec| {
                tokio::spawn(sender.clone().send(rec).map(|_| ()).map_err(|e| {
                    log::error!("Failed to send fid: {}", e);
                    ()
                }))
            }),
    )
    .map(move |_| name)
    .map_err(|_| ImlAgentError::SendError)
}
