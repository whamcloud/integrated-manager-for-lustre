// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

#![allow(non_upper_case_globals)]
#![allow(non_camel_case_types)]
#![allow(non_snake_case)]

include!("bindings.rs");

type lstat_t = libc::stat64;
pub const IOC_MDC_GETFILEINFO: u32 = 0xc0086916;

#[cfg(test)]
mod tests {}
