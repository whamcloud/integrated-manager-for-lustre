// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

#![allow(non_upper_case_globals)]
#![allow(non_camel_case_types)]
#![allow(non_snake_case)]
#![crate_name = "llapi"]

pub mod raw {
    include!("bindings.rs");
}
use std::convert::From;
use std::fmt;
use std::ffi::{CStr, CString};
use std::io;
static PATH_BYTES: usize = 4096;

// pub struct Statfs {
//     pub type: i64;
//     pub block: i64;
// }
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
// impl From<String> for Fid {
//     fn from(fidstr: String) -> Self {
//     }
// }
impl From<raw::lu_fid> for Fid {
    fn from(fid: raw::lu_fid) -> Self {
        Fid { seq: fid.f_seq,
              oid: fid.f_oid,
              ver: fid.f_ver,
        }
    }
}

pub fn fid2path(device: &String, fidstr: &String) -> Option<String> {
    if !fidstr.starts_with("[") {
        return None;
    }

    let mut buf = Vec::with_capacity(PATH_BYTES);

    let devptr = device.as_ptr() as *const i8;
    let fidptr = fidstr.as_ptr() as *const i8;

    let ptr = buf.as_mut_ptr() as *mut i8;

    let rc = unsafe {
        let mut recno: i64 = 0;
        let mut linkno: i32 = 0;
        raw::llapi_fid2path(
            devptr,
            fidptr,
            ptr,
            buf.capacity() as i32,
            &mut recno as *mut std::os::raw::c_longlong,
            &mut linkno as *mut std::os::raw::c_int,
        )
    };
    if rc != 0 {
        return None;
    }

    unsafe {
        let s = CStr::from_ptr(ptr);
        let len = s.to_bytes().len();
        buf.set_len(len);
    };

    let cstr = CString::new(buf).expect("Found invalid UTF-8");

    Some(cstr.into_string().expect("Invalid UTF-8"))
}

//pub fn obd_statfs(filepath: &String) -> Option<raw::obd_statfs> {

    //Some(raw::obd_statfs { })
//}

pub fn rmfid(device: &String, fidlist: &Vec<String>) -> Result<(), io::Error> {
    use std::fs; // replace with raw::llapi_rmfid
    for fidstr in fidlist.iter() {
        if let Some(path) = fid2path(device, fidstr) {
            fs::remove_file(path)?;
        }
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn fid_display() {
        let fid = Fid { ver: 1, oid: 2, seq: 64 };
        assert_eq!("[0x40:0x2:0x1]", format!("{}", fid))
    }
}
