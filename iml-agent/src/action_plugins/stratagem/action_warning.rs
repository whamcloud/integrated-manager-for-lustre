// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::ImlAgentError, env, fidlist, http_comms::mailbox_client};
use csv;
use futures::{
    future::{self, poll_fn, Either, IntoFuture},
    sync::mpsc::channel,
    Future, Sink, Stream,
};
use libc;
use liblustreapi::Llapi;
use std::ffi::CStr;
use std::io;
use std::path::PathBuf;
use tokio_threadpool::blocking;

pub use liblustreapi::is_ok;

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

fn fid2record(llapi: &Llapi, fli: &fidlist::FidListItem) -> Result<Record, ImlAgentError> {
    let mntpt: &str = &*llapi.mntpt()?;
    let path = llapi.fid2path(&fli.fid).map_err(|e| {
        log::error!("Failed to fid2path: {}: {}", fli.fid, e);
        e
    })?;

    let pb: std::path::PathBuf = [mntpt, &path].iter().collect();
    let stat = llapi.mdc_stat(&pb).map_err(|e| {
        log::error!("Failed to mdc_stat({:?}) => {}", pb, e);
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

fn search_rootpath(device: String) -> impl Future<Item = Llapi, Error = ImlAgentError> {
    poll_fn(move || {
        blocking(|| Llapi::search(&device))
            .map_err(|_| panic!("the threadpool shut down"))
    })
    .and_then(std::convert::identity)
    .from_err()
}

pub fn write_records(
    device: &str,
    args: impl IntoIterator<Item = String>,
    out: impl io::Write,
) -> Result<(), ImlAgentError> {
    let llapi = Llapi::search(&device).map_err(|e| {
        log::error!("Failed to find rootpath({}) -> {}", device, e);
        e
    })?;

    let mut wtr = csv::Writer::from_writer(out);

    for fid in args {
        let rec = match fid2record(&llapi, &fidlist::FidListItem::new(fid)) {
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
    (fsname_or_mntpath, mailbox): (String, String),
) -> impl Future<Item = PathBuf, Error = ImlAgentError> {
    let mbox = mailbox.to_string();

    let mut fpath = PathBuf::from(env::get_var_else("REPORT_DIR", "/tmp"));
    fpath.push(mailbox);
    fpath.set_extension("csv");

    let mut wtr = match csv::Writer::from_path(&fpath) {
        Ok(w) => w,
        Err(e) => {
            log::error!("Failed open writer ({:?}) -> {}", fpath, e);
            return Either::B(future::err(ImlAgentError::CsvError(e)));
        }
    };

    let (sender, recv) = channel(4096);

    let f1 = recv
        .map_err(|()| ImlAgentError::UnexpectedStatusError)
        .for_each(move |rec: Record| wtr.serialize(&rec).map_err(ImlAgentError::CsvError));

    let f2 = search_rootpath(fsname_or_mntpath).and_then(move |llapi| {
        mailbox_client::get(mbox)
            .filter_map(|x| {
                x.trim()
                    .split(' ')
                    .filter(|x| x != &"")
                    .last()
                    .map(|x| fidlist::FidListItem::new(x.into()))
            })
            .for_each(move |fli| {
                let sender2 = sender.clone();
                tokio::spawn(
                    poll_fn(move || {
                        blocking(|| fid2record(&llapi, &fli))
                            .map_err(|_| panic!("the threadpool shut down"))
                    })
                    .and_then(std::convert::identity)
                    .map_err(|_| ())
                    .and_then(|rec| {
                        sender2.send(rec).map_err(|e| {
                            log::error!("Failed to send fid: {}", e);
                        })
                    })
                    .map(|_| ()),
                )
                .into_future()
                .map_err(|()| ImlAgentError::UnexpectedStatusError)
            })
    });

    Either::A(f1.join(f2).map(move |_| fpath))
}
