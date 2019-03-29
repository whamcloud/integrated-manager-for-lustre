// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use std::convert::From;
use std::ffi::{CStr, CString};
use std::fmt;
use std::io;
use std::path::PathBuf;
extern crate errno;
extern crate libc;
extern crate liblustreapi_sys as sys;
static PATH_BYTES: usize = 4096;

// FID

#[derive(Copy, Clone)]
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
fn num2u32(num: &str) -> u32 {
    u32::from_str_radix(num.to_lowercase().trim_start_matches("0x"), 16).unwrap()
}
fn num2u64(num: &str) -> u64 {
    u64::from_str_radix(num.to_lowercase().trim_start_matches("0x"), 16).unwrap()
}
impl From<String> for Fid {
    fn from(fidstr: String) -> Self {
        let fidstr = fidstr.trim_matches(|c| c == '[' || c == ']');
        let arr: Vec<&str> = fidstr.split(':').collect();
        Fid {
            seq: num2u64(arr[0]),
            oid: num2u32(arr[1]),
            ver: num2u32(arr[2]),
        }
    }
}
impl From<[u8; 40usize]> for Fid {
    fn from(fidstr: [u8; 40usize]) -> Self {
        Fid::from(String::from_utf8_lossy(&fidstr).into_owned())
    }
}
impl From<sys::lu_fid> for Fid {
    fn from(fid: sys::lu_fid) -> Self {
        Fid {
            seq: fid.f_seq,
            oid: fid.f_oid,
            ver: fid.f_ver,
        }
    }
}

fn buf2string(mut buf: Vec<u8>) -> Result<String, io::Error> {
    unsafe {
        let s = CStr::from_ptr(buf.as_ptr() as *const i8);
        let len = s.to_bytes().len();
        buf.set_len(len);
    };

    let cstr = CString::new(buf);
    match cstr {
        Err(x) => Err(io::Error::new(io::ErrorKind::InvalidData, x)),
        Ok(x) => x
            .into_string()
            .map_err(|x| io::Error::new(io::ErrorKind::InvalidData, x)),
    }
}

pub fn fid2path(device: &str, fidstr: &str) -> Result<String, io::Error> {
    if !fidstr.starts_with('[') {
        return Err(io::Error::new(
            io::ErrorKind::InvalidInput,
            format!("FID is invalid format {}", fidstr),
        ));
    }

    let mut buf = Vec::with_capacity(PATH_BYTES);

    let devptr = device.as_ptr() as *const i8;
    let fidptr = fidstr.as_ptr() as *const i8;

    let ptr = buf.as_mut_ptr() as *mut i8;

    let rc = unsafe {
        let mut recno: i64 = 0;
        let mut linkno: i32 = 0;
        sys::llapi_fid2path(
            devptr,
            fidptr,
            ptr,
            buf.capacity() as i32,
            &mut recno as *mut std::os::raw::c_longlong,
            &mut linkno as *mut std::os::raw::c_int,
        )
    };
    if rc != 0 {
        return Err(io::Error::from_raw_os_error(rc.abs()));
    }

    buf2string(buf)
}

pub fn search_rootpath(fsname: &String) -> Result<String, io::Error> {
    if fsname.starts_with("/") {
        return Ok(fsname.to_string());
    }
    let fsc = CString::new(fsname.as_bytes())
        .map_err(|x| io::Error::new(io::ErrorKind::InvalidData, x))?;
    let mut page: Vec<u8> = Vec::with_capacity(libc::PATH_MAX as usize);
    let rc = unsafe { sys::llapi_search_rootpath(page.as_mut_ptr() as *mut i8, fsc.as_ptr()) };
    if rc != 0 {
        eprintln!(
            "Error: llapi_serach_rootpath({}) => {}",
            fsc.into_string().unwrap(),
            rc
        );
        return Err(io::Error::from_raw_os_error(rc.abs()));
    }
    buf2string(page)
}

pub fn mdc_stat(pathname: &str) -> Result<libc::stat64, io::Error> {
    let page = Vec::with_capacity(libc::PATH_MAX as usize);
    let path = PathBuf::from(pathname);
    let file = path.file_name().unwrap().to_str().unwrap();
    let dir = path.parent().unwrap();

    let rc = unsafe {
        libc::memcpy(
            page.as_ptr() as *mut libc::c_void,
            file.as_ptr() as *const libc::c_void,
            file.len(),
        );

        let dircstr = CString::new(dir.to_str().unwrap()).unwrap();
        let dirptr = dircstr.as_ptr() as *const i8;
        let dirhandle = libc::opendir(dirptr);
        if dirhandle.is_null() {
            let err: i32 = errno::errno().into();
            eprintln!("Failed top opendir({:?}) -> {}", dircstr, err);
            return Err(io::Error::from(io::Error::from_raw_os_error(err)));
        }
        let rc = libc::ioctl(
            libc::dirfd(dirhandle),
            sys::IOC_MDC_GETFILEINFO as u64,
            page.as_ptr() as *mut sys::lov_user_mds_data_v1,
        );
        libc::closedir(dirhandle);
        rc
    };
    if rc != 0 {
        eprintln!("Failed ioctl({}) => {}", dir.to_str().unwrap(), rc);
        return Err(io::Error::from_raw_os_error(rc.abs()));
    }
    let statptr: *const libc::stat64 = page.as_ptr();
    let stat: libc::stat64 = unsafe { *statptr };

    Ok(stat)
}

pub fn rmfid(device: &String, fidlist: impl IntoIterator<Item = String>) -> Result<(), io::Error> {
    use std::fs; // replace with sys::llapi_rmfid
    let mntpt = match search_rootpath(&device) {
        Ok(p) => p,
        Err(e) => {
            eprintln!("Failed to find rootpath({}) -> {:?}", device, e);
            return Err(e);
        }
    };

    for fidstr in fidlist {
        let path = fid2path(device, &fidstr)?;
        let pb: std::path::PathBuf = [&mntpt, &path].iter().collect();
        let fullpath = pb.to_str().unwrap();
        fs::remove_file(fullpath)?;
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
        let fid = sys::lu_fid {
            f_ver: 1,
            f_oid: 4,
            f_seq: 64,
        };
        assert_eq!("[0x40:0x4:0x1]", format!("{}", Fid::from(fid)))
    }

    #[test]
    fn string2fid() {
        assert_eq!(
            "[0x404:0x40:0x10]",
            format!("{}", Fid::from("[0x404:0x40:0x10]".to_string()))
        )
    }
}
