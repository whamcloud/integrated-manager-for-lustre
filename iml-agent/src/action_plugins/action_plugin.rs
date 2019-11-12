// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    action_plugins::{
        check_ha, check_stonith,
        ntp::action_configure,
        ostpool, package_installed,
        stratagem::{action_purge, action_warning, server},
    },
    systemd,
};
use iml_util::action_plugins;
use iml_wire_types::ActionName;
use tracing::info;

/// The registry of available actions to the `AgentDaemon`.
/// Add new Actions to the fn body as they are created.
pub fn create_registry() -> action_plugins::Actions {
    let map = action_plugins::Actions::new()
        .add_plugin("start_unit", systemd::start_unit)
        .add_plugin("stop_unit", systemd::stop_unit)
        .add_plugin("enable_unit", systemd::enable_unit)
        .add_plugin("disable_unit", systemd::disable_unit)
        .add_plugin("restart_unit", systemd::restart_unit)
        .add_plugin("get_unit_run_state", systemd::get_run_state)
        .add_plugin("package_installed", package_installed::package_installed)
        .add_plugin("start_scan_stratagem", server::trigger_scan)
        .add_plugin("stream_fidlists_stratagem", server::stream_fidlists)
        .add_plugin("action_warning_stratagem", action_warning::read_mailbox)
        .add_plugin("action_purge_stratagem", action_purge::read_mailbox)
        .add_plugin("action_check_ha", check_ha::check_ha)
        .add_plugin("action_check_stonith", check_stonith::check_stonith)
        .add_plugin("ostpool_create", ostpool::action_pool_create)
        .add_plugin("ostpool_wait", ostpool::action_pool_wait)
        .add_plugin("ostpool_destroy", ostpool::action_pool_destroy)
        .add_plugin("ostpool_add", ostpool::action_pool_add)
        .add_plugin("ostpool_remove", ostpool::action_pool_remove)
        .add_plugin(
            "configure_ntp",
            action_configure::update_and_write_new_config,
        );

    info!("Loaded the following ActionPlugins:");

    for ActionName(key) in map.keys() {
        info!("{}", key)
    }

    map
}
