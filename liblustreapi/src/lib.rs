// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub mod error;

use error::LiblustreError;
use libloading::{Library, Symbol};
use liblustreapi_types as types;
use std::{
    convert::From,
    ffi::{CStr, CString},
    fmt, io,
    num::ParseIntError,
    os::unix::ffi::OsStrExt,
    path::PathBuf,
    str::FromStr,
    sync::Arc,
};

const PATH_BYTES: usize = 4096;

const LIBLUSTRE: &str = "liblustreapi.so.1";

pub const MAXFSNAME: usize = types::LUSTRE_MAXFSNAME as usize;

// FID

#[repr(C)]
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

impl From<Fid> for types::lu_fid {
    fn from(fid: Fid) -> Self {
        Self {
            f_seq: fid.seq,
            f_oid: fid.oid,
            f_ver: fid.ver,
        }
    }
}

#[repr(C)]
#[derive(Debug, Copy, Clone)]
pub struct FidArrayHdr {
    pub nr: u32,
    pub pad0: u32,
    pub pad1: u64,
}

impl FidArrayHdr {
    pub fn new(num: u32) -> Self {
        FidArrayHdr {
            nr: num,
            pad0: 0,
            pad1: 0,
        }
    }
}

#[repr(C)]
#[derive(Copy, Clone)]
pub union RmfidsArg {
    pub hdr: FidArrayHdr,
    pub fid: Fid,
}

impl From<FidArrayHdr> for RmfidsArg {
    fn from(hdr: FidArrayHdr) -> Self {
        Self { hdr }
    }
}

impl From<Fid> for RmfidsArg {
    fn from(fid: Fid) -> Self {
        Self { fid }
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

// LLAPI

#[derive(Clone, Debug)]
pub struct Llapi {
    lib: Arc<Library>,
}

impl Llapi {
    pub fn create() -> Result<Llapi, LiblustreError> {
        let lib = unsafe { Library::new(LIBLUSTRE)? };
        Ok(Llapi { lib: Arc::new(lib) })
    }
    /// Get a pointer to function or static variable by symbol name
    ///
    /// # Safety
    ///
    /// Pointer to a value of arbitrary type is returned. Using a value with wrong type is
    /// undefined.
    pub unsafe fn get<T>(&self, symbol: &[u8]) -> Result<Symbol<'_, T>, LiblustreError> {
        let x = self.lib.get(symbol)?;

        Ok(x)
    }

    pub fn mdc_stat(&self, path: &PathBuf) -> Result<types::lstat_t, LiblustreError> {
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
            .ok_or_else(|| {
                LiblustreError::not_found(format!("No string for Parent: {:?}", path))
            })?;

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
            tracing::error!("Failed top opendir({:?}) -> {}", dircstr, e);
            return Err(LiblustreError::os_error(e.into()));
        }

        let fd = unsafe { libc::dirfd(dirhandle) };

        if fd < 0 {
            let e = errno::errno();
            tracing::error!("Failed dirfd({:?}) => {}", dirhandle, e);
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
            tracing::error!("Failed ioctl({:?}) => {}", path, e);
            return Err(LiblustreError::os_error(e.into()));
        }

        let rc = unsafe { libc::closedir(dirhandle) };

        if rc < 0 {
            let e = errno::errno();
            tracing::error!("Failed closedir({:?}) => {}", dirhandle, e);
            return Err(LiblustreError::os_error(e.into()));
        }

        let statptr: *const types::lstat_t = page.as_ptr();
        let stat: types::lstat_t = unsafe { *statptr };

        Ok(stat)
    }

    pub fn fid2path(&self, mntpt: &str, fidstr: &str) -> Result<String, LiblustreError> {
        if !fidstr.starts_with('[') {
            return Err(LiblustreError::invalid_input(format!(
                "FID is invalid format {}",
                fidstr
            )));
        }

        let mut buf: Vec<u8> = vec![0; std::mem::size_of::<u8>() * PATH_BYTES];
        let ptr = buf.as_mut_ptr() as *mut libc::c_char;

        let devptr = CString::new(mntpt)?.into_raw();
        let fidptr = CString::new(fidstr)?.into_raw();

        let mut recno: i64 = -1;
        let mut linkno: i32 = 0;

        let f = unsafe { self.get(b"llapi_fid2path\0")? };

        let func: Symbol<
            extern "C" fn(
                *const libc::c_char,
                *const libc::c_char,
                *mut libc::c_char,
                libc::c_int,
                *mut libc::c_longlong,
                *mut libc::c_int,
            ) -> libc::c_int,
        > = f;

        let rc = func(
            devptr,
            fidptr,
            ptr,
            buf.len() as i32,
            &mut recno as *mut std::os::raw::c_longlong,
            &mut linkno as *mut std::os::raw::c_int,
        );

        unsafe {
            // Ensure CStrings are freed
            let _ = CString::from_raw(devptr);
            let _ = CString::from_raw(fidptr);
        }

        if rc != 0 {
            return Err(LiblustreError::os_error(rc.abs()));
        }

        buf2string(buf)
    }

    pub fn path2fid(&self, _mntpt: &str, path: &PathBuf) -> Result<String, LiblustreError> {
        let pathptr = CString::new(path.to_str().unwrap())?.into_raw();
        let mut fid = Fid {
            seq: 0,
            oid: 0,
            ver: 0,
        };

        let f = unsafe { self.lib.get(b"llapi_path2fid\0")? };

        let func: Symbol<extern "C" fn(*const libc::c_char, *mut Fid) -> libc::c_int> = f;
        let rc = func(pathptr, &mut fid as *mut Fid);

        unsafe {
            // Ensure CStrings are freed
            let _ = CString::from_raw(pathptr);
        }

        if rc != 0 {
            return Err(LiblustreError::os_error(rc.abs()));
        }

        Ok(fid.to_string())
    }

    pub fn search_fsname(&self, pathname: &str) -> Result<String, LiblustreError> {
        let mut path = PathBuf::from(pathname);
        let md = std::fs::symlink_metadata(&path)?;
        if md.file_type().is_symlink() {
            path.pop();
        }

        let fsc = CString::new(path.into_os_string().as_bytes())?;
        let mut fsname: Vec<u8> = vec![0; std::mem::size_of::<u8>() * MAXFSNAME + 1];
        let ptr = fsname.as_mut_ptr() as *mut libc::c_char;

        let f = unsafe { self.lib.get(b"llapi_search_fsname\0")? };

        let func: Symbol<extern "C" fn(*const libc::c_char, *mut libc::c_char) -> libc::c_int> = f;
        let rc = func(fsc.as_ptr(), ptr);

        if rc != 0 {
            tracing::error!("Error: llapi_search_fsname({}) => {}", pathname, rc);
            return Err(LiblustreError::os_error(rc.abs()));
        }

        buf2string(fsname)
    }

    pub fn search_rootpath(&self, tmp_fsname: &str) -> Result<String, LiblustreError> {
        let mut fsname = tmp_fsname.to_string();

        if fsname.starts_with('/') {
            fsname = Llapi::search_fsname(self, &fsname)?;
        }

        let fsc = CString::new(fsname.as_bytes())?;

        let mut page: Vec<u8> = vec![0; std::mem::size_of::<u8>() * PATH_BYTES];
        let ptr = page.as_mut_ptr() as *mut libc::c_char;

        let f = unsafe { self.get(b"llapi_search_rootpath\0")? };

        let func: Symbol<extern "C" fn(*mut libc::c_char, *const libc::c_char) -> libc::c_int> = f;

        let rc = func(ptr, fsc.as_ptr());

        if rc != 0 {
            tracing::error!("Error: llapi_search_rootpath({}) => {}", fsname, rc);
            return Err(LiblustreError::os_error(rc.abs()));
        }

        buf2string(page)
    }

    fn llapi_rmfid(&self, mntpt: &str, fidlist: &[String]) -> Result<(), LiblustreError> {
        let func: Symbol<extern "C" fn(*const libc::c_char, *const RmfidsArg) -> libc::c_int> =
            unsafe { self.get(b"llapi_rmfid\0")? };

        let devptr = CString::new(mntpt).map(|c| c.into_raw())?;

        let mut fids: Vec<RmfidsArg> = Vec::with_capacity(fidlist.len() + 1);
        fids.push(FidArrayHdr::new(0).into());

        for fidstr in fidlist {
            if let Ok(fid) = Fid::from_str(&fidstr) {
                fids.push(fid.into());
            } else {
                tracing::error!("Bad fid format: {}", fidstr);
            }
        }

        fids[0].hdr.nr = fids.len() as u32 - 1;

        let rc = func(devptr, fids.as_ptr());

        // Ensure CString is freed
        unsafe {
            let _ = CString::from_raw(devptr);
        }

        if rc == 0 {
            Ok(())
        } else {
            Err(io::Error::new(
                io::ErrorKind::Other,
                format!(
                    "Call to llapi_rmfids({}, [{}, ...]) failed: {}",
                    &mntpt,
                    unsafe { fids[0].hdr.nr },
                    rc
                ),
            )
            .into())
        }
    }

    pub fn rmfids(&self, mntpt: &str, fidlist: Vec<String>) -> Result<(), LiblustreError> {
        self.llapi_rmfid(&mntpt, &fidlist)
    }

    pub fn rmfids_size(&self) -> usize {
        types::OBD_MAX_FIDS_IN_ARRAY as usize
    }
}

// LLAPI + Mountpoint

#[derive(Clone, Debug)]
pub struct LlapiFid {
    llapi: Llapi,
    mntpt: String,
}

impl LlapiFid {
    pub fn create(fsname_or_mntpt: &str) -> Result<LlapiFid, LiblustreError> {
        let llapi = Llapi::create()?;
        let mntpt = llapi.search_rootpath(fsname_or_mntpt)?;
        Ok(LlapiFid { llapi, mntpt })
    }
    pub fn mntpt(&self) -> String {
        self.mntpt.clone()
    }

    // from llapi
    pub fn mdc_stat(&self, path: &PathBuf) -> Result<types::lstat_t, LiblustreError> {
        self.llapi.mdc_stat(path)
    }
    pub fn fid2path(&self, fidstr: &str) -> Result<String, LiblustreError> {
        self.llapi.fid2path(&self.mntpt, fidstr)
    }
    pub fn path2fid(&self, path: &PathBuf) -> Result<String, LiblustreError> {
        self.llapi.path2fid(&self.mntpt, path)
    }
    pub fn search_rootpath(&mut self, fsname: &str) -> Result<String, LiblustreError> {
        let s = self.llapi.search_rootpath(fsname)?;
        self.mntpt = s.clone();
        Ok(s)
    }
    pub fn search_fsname(&self, pathname: &str) -> Result<String, LiblustreError> {
        self.llapi.search_fsname(pathname)
    }
    pub fn rmfids(&self, fidlist: Vec<String>) -> Result<(), LiblustreError> {
        self.llapi.rmfids(&self.mntpt, fidlist)
    }
    pub fn rmfids_size(&self) -> usize {
        self.llapi.rmfids_size()
    }
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

    #[test]
    fn test_layout_rmfids_arg() {
        assert_eq!(
            ::std::mem::size_of::<RmfidsArg>(),
            16usize,
            concat!("Size of: ", stringify!(RmfidsArg))
        );
        assert_eq!(
            ::std::mem::align_of::<RmfidsArg>(),
            8usize,
            concat!("Alignment of ", stringify!(RmfidsArg))
        );
        assert_eq!(
            ::std::mem::size_of::<RmfidsArg>(),
            ::std::mem::size_of::<Fid>(),
            concat!("Size of: ", stringify!(RmfidsArg))
        );
    }
}
