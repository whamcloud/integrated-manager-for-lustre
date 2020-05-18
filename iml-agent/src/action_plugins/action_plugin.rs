// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::action_plugins::{
    check_kernel, check_stonith, firewall_cmd, high_availability, kernel_module, lamigo, lpurge,
    ltuer, lustre,
    ntp::{action_configure, is_ntp_configured},
    ostpool, package, postoffice,
    stratagem::{action_purge, action_warning, server},
};
use iml_util::action_plugins;
use iml_wire_types::ActionName;
use tracing::info;

/// The registry of available actions to the `AgentDaemon`.
/// Add new Actions to the fn body as they are created.
pub fn create_registry() -> action_plugins::Actions {
    let map = action_plugins::Actions::default()
        .add_plugin("start_unit", iml_systemd::start_unit)
        .add_plugin("stop_unit", iml_systemd::stop_unit)
        .add_plugin("enable_unit", iml_systemd::enable_unit)
        .add_plugin("disable_unit", iml_systemd::disable_unit)
        .add_plugin("restart_unit", iml_systemd::restart_unit)
        .add_plugin("get_unit_run_state", iml_systemd::get_run_state)
        .add_plugin("kernel_module_loaded", kernel_module::loaded)
        .add_plugin("kernel_module_version", kernel_module::version)
        .add_plugin("package_installed", package::installed)
        .add_plugin("package_version", package::version)
        .add_plugin("start_scan_stratagem", server::trigger_scan)
        .add_plugin("stream_fidlists_stratagem", server::stream_fidlists)
        .add_plugin("action_warning_stratagem", action_warning::read_mailbox)
        .add_plugin("action_purge_stratagem", action_purge::read_mailbox)
        .add_plugin("action_check_ha", high_availability::check_ha)
        .add_plugin("action_check_stonith", check_stonith::check_stonith)
        .add_plugin("get_kernel", check_kernel::get_kernel)
        .add_plugin(
            "get_ha_resource_list",
            high_availability::get_ha_resource_list,
        )
        .add_plugin("try_mount", lustre::try_mount)
        .add_plugin("crm_attribute", high_availability::crm_attribute)
        .add_plugin(
            "change_mcast_port",
            high_availability::corosync_conf::change_mcast_port,
        )
        .add_plugin("add_firewall_port", firewall_cmd::add_port)
        .add_plugin("remove_firewall_port", firewall_cmd::remove_port)
        .add_plugin("pcs", high_availability::pcs)
        .add_plugin("lctl", lustre::lctl)
        .add_plugin("ostpool_create", ostpool::action_pool_create)
        .add_plugin("ostpool_wait", ostpool::action_pool_wait)
        .add_plugin("ostpool_destroy", ostpool::action_pool_destroy)
        .add_plugin("ostpool_add", ostpool::action_pool_add)
        .add_plugin("ostpool_remove", ostpool::action_pool_remove)
        .add_plugin("postoffice_add", postoffice::route_add)
        .add_plugin("postoffice_remove", postoffice::route_remove)
        .add_plugin("create_lpurge_conf", lpurge::create_lpurge_conf)
        .add_plugin("create_lamigo_service", lamigo::create_lamigo_service_unit)
        .add_plugin(
            "configure_ntp",
            action_configure::update_and_write_new_config,
        )
        .add_plugin("is_ntp_configured", is_ntp_configured::is_ntp_configured)
        .add_plugin("create_ltuer_conf", ltuer::create_ltuer_conf)
        // Task Actions
        .add_plugin("action.stratagem.warning", action_warning::process_fids)
        .add_plugin("action.stratagem.purge", action_purge::process_fids);

    info!("Loaded the following ActionPlugins:");

    for ActionName(key) in map.keys() {
        info!("{}", key)
    }

    map
}
