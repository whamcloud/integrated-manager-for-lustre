// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub use crate::models::{ChromaCoreMailbox, LustreFid};
use crate::schema::chroma_core_mailbox as mb;
use diesel::{dsl, prelude::*};
use std::{convert::From, fmt, str::FromStr};

impl fmt::Display for LustreFid {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "[0x{:x}:0x{:x}:0x{:x}]", self.seq, self.oid, self.ver)
    }
}
impl FromStr for LustreFid {
    type Err = std::num::ParseIntError;
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

impl From<[u8; 40_usize]> for LustreFid {
    fn from(fidstr: [u8; 40_usize]) -> Self {
        String::from_utf8_lossy(&fidstr)
            .into_owned()
            .parse::<Self>()
            .unwrap()
    }
}

pub type WithName = dsl::Eq<mb::name, String>;
pub type ByName = dsl::Filter<mb::table, WithName>;

impl ChromaCoreMailbox {
    pub fn with_name(name: impl ToString) -> WithName {
        mb::name.eq(name.to_string())
    }
    pub fn by_name(name: impl ToString) -> ByName {
        mb::table.filter(Self::with_name(name))
    }
}
