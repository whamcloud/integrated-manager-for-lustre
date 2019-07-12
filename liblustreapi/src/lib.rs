// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub mod error;

use errno;
use error::LiblustreError;
use libc;
use libloading as lib;
use liblustreapi_types as types;
use log;
use std::{
    convert::From,
    ffi::{CStr, CString},
    fmt,
    num::ParseIntError,
    path::PathBuf,
    str::FromStr,
};

const PATH_BYTES: usize = 4096;

const LIBLUSTRE: &'static str = "liblustreapi.so.1";

// FID

#[derive(Copy, Clone, Debug, PartialEq)]
pub struct Fid {
    pub seq: u64,
    pub oid: u32,
    pub ver: u32,
}
impl fmt::Display for Fid {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "[0x{:x}:0x{:x}:0x{:x}]", self.seq, self.oid, self.ver)
    }
}
impl FromStr for Fid {
    type Err = ParseIntError;
    fn from_str(s: &str) -> Result<Self, Self::Err> {
        let fidstr = s.trim_matches(|c| c == '[' || c == ']');
        let arr: Vec<&str> = fidstr
            .split(':')
            .map(|num| num.trim_start_matches("0x"))
            .collect();
        Ok(Self {
            seq: u64::from_str_radix(arr[0], 16)?,
            oid: u32::from_str_radix(arr[1], 16)?,
            ver: u32::from_str_radix(arr[2], 16)?,
        })
    }
}
impl From<[u8; 40_usize]> for Fid {
    fn from(fidstr: [u8; 40_usize]) -> Self {
        String::from_utf8_lossy(&fidstr)
            .into_owned()
            .parse::<Self>()
            .unwrap()
    }
}
impl From<types::lu_fid> for Fid {
    fn from(fid: types::lu_fid) -> Self {
        Self {
            seq: fid.f_seq,
            oid: fid.f_oid,
            ver: fid.f_ver,
        }
    }
}

fn buf2string(mut buf: Vec<u8>) -> Result<String, LiblustreError> {
    unsafe {
        let s = CStr::from_ptr(buf.as_ptr() as *const i8);
        let len = s.to_bytes().len();
        buf.set_len(len);
    };

    Ok(CString::new(buf)?.into_string()?)
}

pub fn is_ok() -> bool {
    lib::Library::new(LIBLUSTRE).is_ok()
}

pub fn fid2path(device: &str, fidstr: &str) -> Result<String, LiblustreError> {
    if !fidstr.starts_with('[') {
        return Err(LiblustreError::invalid_input(format!(
            "FID is invalid format {}",
            fidstr
        )));
    }

    let lib = lib::Library::new(LIBLUSTRE).map_err(LiblustreError::not_loaded)?;

    let mut buf: Vec<u8> = vec![0; std::mem::size_of::<u8>() * PATH_BYTES];
    let ptr = buf.as_mut_ptr() as *mut libc::c_char;

    let devptr = CString::new(device)?.into_raw();
    let fidptr = CString::new(fidstr)?.into_raw();

    let rc = unsafe {
        let mut recno: i64 = -1;
        let mut linkno: i32 = 0;
        let rc = match lib.get(b"llapi_fid2path\0") {
            Ok(f) => {
                let func: lib::Symbol<
                    extern "C" fn(
                        *const libc::c_char,
                        *const libc::c_char,
                        *mut libc::c_char,
                        libc::c_int,
                        *mut libc::c_longlong,
                        *mut libc::c_int,
                    ) -> libc::c_int,
                > = f;
                func(
                    devptr,
                    fidptr,
                    ptr,
                    buf.len() as i32,
                    &mut recno as *mut std::os::raw::c_longlong,
                    &mut linkno as *mut std::os::raw::c_int,
                )
            }
            Err(_) => 1, // @@
        };
        // Ensure CStrings are freed
        let _ = CString::from_raw(devptr);
        let _ = CString::from_raw(fidptr);
        rc
    };

    if rc != 0 {
        return Err(LiblustreError::os_error(rc.abs()));
    }

    buf2string(buf)
}

pub fn search_rootpath(fsname: &str) -> Result<String, LiblustreError> {
    // @TODO this should do more validation
    if fsname.starts_with('/') {
        return Ok(fsname.to_string());
    }
    let lib = lib::Library::new(LIBLUSTRE).map_err(LiblustreError::not_loaded)?;
    let fsc = CString::new(fsname.as_bytes())?;

    let mut page: Vec<u8> = vec![0; std::mem::size_of::<u8>() * PATH_BYTES];
    let ptr = page.as_mut_ptr() as *mut libc::c_char;

    let rc = unsafe {
        match lib.get(b"llapi_search_rootpath\0") {
            Ok(f) => {
                let func: lib::Symbol<
                    extern "C" fn(*mut libc::c_char, *const libc::c_char) -> libc::c_int,
                > = f;
                func(ptr, fsc.as_ptr())
            }
            Err(_) => 1, // @@
        }
    };

    if rc != 0 {
        log::error!(
            "Error: llapi_search_rootpath({}) => {}",
            fsc.into_string()?,
            rc
        );
        return Err(LiblustreError::os_error(rc.abs()));
    }

    buf2string(page)
}

pub fn mdc_stat(path: &PathBuf) -> Result<types::lstat_t, LiblustreError> {
    let file_name = path
        .file_name()
        .ok_or_else(|| LiblustreError::not_found(format!("File Not Found: {:?}", path)))?
        .to_str()
        .ok_or_else(|| LiblustreError::not_found(format!("No string for File: {:?}", path)))?;

    let file_namec = CString::new(file_name)?;

    let dirstr = path
        .parent()
        .ok_or_else(|| LiblustreError::not_found(format!("No Parent directory: {:?}", path)))?
        .to_str()
        .ok_or_else(|| LiblustreError::not_found(format!("No string for Parent: {:?}", path)))?;

    let dircstr = CString::new(dirstr)?;

    let page = Vec::with_capacity(PATH_BYTES);

    unsafe {
        libc::memcpy(
            page.as_ptr() as *mut libc::c_void,
            file_namec.as_ptr() as *const libc::c_void,
            file_namec.as_bytes_with_nul().len(),
        );
    }

    let dirhandle = unsafe { libc::opendir(dircstr.as_ptr() as *const i8) };

    if dirhandle.is_null() {
        let e = errno::errno();
        log::error!("Failed top opendir({:?}) -> {}", dircstr, e);
        return Err(LiblustreError::os_error(e.into()));
    }

    let fd = unsafe { libc::dirfd(dirhandle) };

    if fd < 0 {
        let e = errno::errno();
        log::error!("Failed dirfd({:?}) => {}", dirhandle, e);
        return Err(LiblustreError::os_error(e.into()));
    }

    let rc = unsafe {
        libc::ioctl(
            fd,
            types::IOC_MDC_GETFILEINFO as u64,
            page.as_ptr() as *mut types::lov_user_mds_data_v1,
        )
    };

    if rc < 0 {
        let e = errno::errno();
        log::error!("Failed ioctl({:?}) => {}", path, e);
        return Err(LiblustreError::os_error(e.into()));
    }

    let rc = unsafe { libc::closedir(dirhandle) };

    if rc < 0 {
        let e = errno::errno();
        log::error!("Failed closedir({:?}) => {}", dirhandle, e);
        return Err(LiblustreError::os_error(e.into()));
    }

    let statptr: *const types::lstat_t = page.as_ptr();
    let stat: types::lstat_t = unsafe { *statptr };

    Ok(stat)
}

pub fn rmfid(mntpt: &str, fidstr: &str) -> Result<(), LiblustreError> {
    use std::fs; // @TODO replace with sys::llapi_rmfid once LU-12090 lands

    let path = fid2path(mntpt, &fidstr)?;
    let pb: std::path::PathBuf = [mntpt, &path].iter().collect();
    if let Err(e) = fs::remove_file(pb) {
        log::error!("Failed to remove {}: {:?}", fidstr, e);
    }

    Ok(())
}

pub fn rmfids(
    mntpt: &str,
    fidlist: impl IntoIterator<Item = String>,
) -> Result<(), LiblustreError> {
    // @TODO replace with sys::llapi_rmfid once LU-12090 lands
    for fidstr in fidlist {
        rmfid(&mntpt, &fidstr).unwrap_or_else(|x| {
            log::error!(
                "Couldn't remove fid {} with mountpoint {}: {}.",
                fidstr,
                mntpt,
                x
            )
        });
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn fid_display() {
        let fid = Fid {
            ver: 1,
            oid: 2,
            seq: 64,
        };
        assert_eq!("[0x40:0x2:0x1]", format!("{}", fid))
    }

    #[test]
    fn lu_fid2fid() {
        let fid = types::lu_fid {
            f_ver: 1,
            f_oid: 4,
            f_seq: 64,
        };
        assert_eq!("[0x40:0x4:0x1]", format!("{}", Fid::from(fid)))
    }

    #[test]
    fn string2fid() {
        let fid = Fid {
            seq: 0x404,
            oid: 0x40,
            ver: 0x10,
        };
        assert_eq!(Ok(fid), Fid::from_str("[0x404:0x40:0x10]"))
    }
}
