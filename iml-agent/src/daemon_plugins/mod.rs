// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

//! # `DaemonPlugins`
//!
//! Provides an extensible plugin interface for long-running plugins.
//!
//! `DaemonPlugin` is a trait that can be implemented by stateful plugins.
//! Each plugin is wrapped in a session which provides a connection guarantee with the IML manager.

pub mod action_runner;
pub mod daemon_plugin;
pub mod ntp;
pub mod stratagem;

pub use daemon_plugin::{
    get_plugin, plugin_registry, DaemonBox, DaemonPlugin, DaemonPlugins, Output, OutputValue,
};
