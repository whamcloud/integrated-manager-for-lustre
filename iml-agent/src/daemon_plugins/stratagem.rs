// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::daemon_plugins::DaemonPlugin;

pub fn create() -> impl DaemonPlugin {
    Stratagem {}
}

#[derive(Debug)]
pub struct Stratagem {}

/// This impl is currently a noop.
/// We have no persistent needs for
/// Stratagem yet.
impl DaemonPlugin for Stratagem {}
