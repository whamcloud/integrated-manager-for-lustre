// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

//! Data structures for communicating with the agent regarding lustre client mounts.

#[cfg(feature = "cli")]
use structopt::StructOpt;

#[derive(serde::Deserialize, Debug)]
#[cfg_attr(feature = "cli", derive(StructOpt))]
/// Ask agent to mount a client
pub struct Mount {
    /// mountspec
    pub mountspec: String,
    /// mountpoint
    pub mountpoint: String,
    /// Persist mount across reboots
    #[cfg_attr(feature = "cli", structopt(short = "p", long = "persist"))]
    pub persist: bool,
}

#[derive(serde::Deserialize, Debug)]
#[cfg_attr(feature = "cli", derive(StructOpt))]
/// Ask agent to unmount a client and clear matching `/etc/fstab` entry
pub struct Unmount {
    /// mountspec
    pub mountspec: String,
    /// mountpoint
    pub mountpoint: String,
}
