#![allow(non_upper_case_globals)]
#![allow(non_camel_case_types)]
#![allow(non_snake_case)]
#![crate_name = "llapi"]

pub mod raw {
    include!("bindings.rs");
}
use std::fs; // replace with llapi::rmfid
use std::ffi::{CStr, CString};
static PATH_BYTES: usize = 4096;

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
        println!("Could not lookup {} in {}: {}", fidstr, device, rc);
        return None;
    }

    unsafe {
        let s = CStr::from_ptr(ptr);
        let len = s.to_bytes().len();
        buf.set_len(len);
    };

    let cstr = CString::new(buf).expect("Found invalide UTF-8");

    Some(cstr.into_string().expect("Invalide UTF-8"))
}

#[cfg(test)]
mod tests {}
