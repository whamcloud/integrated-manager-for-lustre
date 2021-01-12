// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

//! # `DaemonPlugins`
//!
//! Provides an extensible plugin interface for long-running plugins.
//!
//! `DaemonPlugin` is a trait that can be implemented by stateful plugins.
//! Each plugin is wrapped in a session which provides a connection guarantee with the EMF manager.

pub mod action_runner;
pub mod corosync;
pub mod daemon_plugin;
pub mod device;
pub mod journal;
pub mod network;
pub mod ntp;
pub mod ostpool;
pub mod postoffice;
pub mod snapshot;
pub mod stats;

pub use daemon_plugin::{
    get_plugin, plugin_registry, DaemonBox, DaemonPlugin, DaemonPlugins, Output, OutputValue,
};
