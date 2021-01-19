// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

#![allow(non_upper_case_globals)]
#![allow(non_camel_case_types)]
#![allow(non_snake_case)]

include!("bindings.rs");

#[cfg(target_os = "macos")]
pub type lstat_t = libc::stat;

#[cfg(target_os = "linux")]
pub type lstat_t = libc::stat64;

pub const IOC_MDC_GETFILEINFO: u32 = 0xc008_6916;
