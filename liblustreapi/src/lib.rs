// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use std::convert::From;
use std::ffi::{CStr, CString};
use std::fmt;
use std::io;
extern crate liblustreapi_sys as sys;
static PATH_BYTES: usize = 4096;

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
// @@ There's got to be a better way to do this!
fn num2u32(num: &str) -> u32 {
    if num.starts_with("0x") {
        u32::from_str_radix(num.trim_start_matches("0x"), 16).unwrap()
    } else if num.starts_with("0X") {
        u32::from_str_radix(num.trim_start_matches("0X"), 16).unwrap()
    } else {
        num.parse().unwrap()
    }
}
fn num2u64(num: &str) -> u64 {
    if num.starts_with("0x") {
        u64::from_str_radix(num.trim_start_matches("0x"), 16).unwrap()
    } else if num.starts_with("0X") {
        u64::from_str_radix(num.trim_start_matches("0X"), 16).unwrap()
    } else {
        num.parse().unwrap()
    }
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

#[derive(Copy, Clone)]
pub struct StatfsState {
    degraded: bool,
    readonly: bool,
    noprecreate: bool,
    enospc: bool,
    enoino: bool,
}
impl fmt::Display for StatfsState {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        let mut list: Vec<String> = vec![];
        if self.degraded {
            list.push("degraded".to_string());
        }
        if self.readonly {
            list.push("readonly".to_string());
        }
        if self.noprecreate {
            list.push("noprecreate".to_string());
        }
        if self.enospc {
            list.push("enospc".to_string());
        }
        if self.enoino {
            list.push("enoino".to_string());
        }
        write!(f, "{}", list.join(","))
    }
}
impl From<u32> for StatfsState {
    fn from(state: u32) -> Self {
        StatfsState {
            degraded: state & sys::obd_statfs_state_OS_STATE_DEGRADED != 0,
            readonly: state & sys::obd_statfs_state_OS_STATE_READONLY != 0,
            noprecreate: state & sys::obd_statfs_state_OS_STATE_NOPRECREATE != 0,
            enospc: state & sys::obd_statfs_state_OS_STATE_ENOSPC != 0,
            enoino: state & sys::obd_statfs_state_OS_STATE_ENOINO != 0,
        }
    }
}

#[derive(Copy, Clone)]
pub struct Statfs {
    pub ostype: u64,
    pub blocks: u64,
    pub bfree: u64,
    pub bavail: u64,
    pub files: u64,
    pub ffree: u64,
    pub fsid: Fid,
    pub bsize: u32,
    pub namelen: u32,
    pub maxbytes: u64,
    pub state: StatfsState,
    pub fprecreated: u32,
}
impl From<sys::obd_statfs> for Statfs {
    fn from(statfs: sys::obd_statfs) -> Self {
        Statfs {
            ostype: statfs.os_type,
            blocks: statfs.os_blocks,
            bfree: statfs.os_bfree,
            bavail: statfs.os_bavail,
            files: statfs.os_files,
            ffree: statfs.os_ffree,
            fsid: Fid::from(statfs.os_fsid),
            bsize: statfs.os_bsize,
            namelen: statfs.os_namelen,
            maxbytes: statfs.os_maxbytes,
            state: StatfsState::from(statfs.os_state),
            fprecreated: statfs.os_fprecreated,
        }
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
        return Err(io::Error::from_raw_os_error(rc));
    }

    unsafe {
        let s = CStr::from_ptr(ptr);
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

// pub fn obd_statfs(filepath: &String) -> Result<Statfs, io::Error> {
//     let mut path = filepath;
//     sys::llapi_obd_statfs(path.as_ptr(),
//     Ok(Statfs::from(statfs))
// }

pub fn rmfid(device: &str, fidlist: impl IntoIterator<Item = String>) -> Result<(), io::Error> {
    use std::fs; // replace with sys::llapi_rmfid

    for fidstr in fidlist {
        let path = fid2path(device, &fidstr)?;
        fs::remove_file(path)?;
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
