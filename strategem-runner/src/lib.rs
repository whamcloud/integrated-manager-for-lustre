#![allow(non_upper_case_globals)]
#![allow(non_camel_case_types)]
#![allow(non_snake_case)]
#![crate_name = "llapi"]

pub mod raw {
    include!("bindings.rs");
}
use std::ffi::{CStr, CString};
use std::io; // for std::io::Result
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

pub fn rmfid(device: &String, fidlist: &Vec<String>) -> io::Result<()> {
    use std::fs; // replace with raw::llapi_rmfid
    for fidstr in fidlist.iter() {
        if let Some(path) = fid2path(device, fidstr) {
            fs::remove_file(path)?;
        }
    }

    Ok(())
}

#[cfg(test)]
mod tests {}
