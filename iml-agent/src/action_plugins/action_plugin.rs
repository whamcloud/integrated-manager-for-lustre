// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    action_plugins::{
        check_kernel, check_stonith, firewall_cmd, high_availability, kernel_module, lamigo, ldev,
        lnet, lpurge, lustre,
        ntp::{action_configure, is_ntp_configured},
        ostpool, package, postoffice,
        stratagem::{
            action_cloudsync, action_filesync, action_mirror, action_purge, action_warning, server,
        },
    },
    lustre::lctl,
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
        .add_plugin("action_check_ha", high_availability::check_ha)
        .add_plugin("action_check_stonith", check_stonith::check_stonith)
        .add_plugin("get_kernel", check_kernel::get_kernel)
        .add_plugin(
            "get_ha_resource_list",
            high_availability::get_ha_resource_list,
        )
        .add_plugin("mount", lustre::client::mount)
        .add_plugin("mount_many", lustre::client::mount_many)
        .add_plugin("unmount", lustre::client::unmount)
        .add_plugin("unmount_many", lustre::client::unmount_many)
        .add_plugin("add_fstab_entry", lustre::client::add_fstab_entry)
        .add_plugin("remove_fstab_entry", lustre::client::remove_fstab_entry)
        .add_plugin("ha_resource_start", high_availability::start_resource)
        .add_plugin("ha_resource_stop", high_availability::stop_resource)
        .add_plugin("ha_resource_move", high_availability::move_resource)
        .add_plugin(
            "ha_resource_create",
            high_availability::create_single_resource,
        )
        .add_plugin(
            "ha_resource_create_cloned",
            high_availability::create_cloned_resource,
        )
        .add_plugin("ha_resource_destroy", high_availability::destroy_resource)
        .add_plugin(
            "ha_cloned_client_create",
            high_availability::create_cloned_client,
        )
        .add_plugin(
            "ha_cloned_client_destroy",
            high_availability::destroy_cloned_client,
        )
        .add_plugin("crm_attribute", high_availability::crm_attribute)
        .add_plugin(
            "change_mcast_port",
            high_availability::corosync_conf::change_mcast_port,
        )
        .add_plugin("add_firewall_port", firewall_cmd::add_port)
        .add_plugin("remove_firewall_port", firewall_cmd::remove_port)
        .add_plugin("pcs", high_availability::pcs)
        .add_plugin("lctl", lctl::<Vec<_>, String>)
        .add_plugin("lnet_load", lnet::load)
        .add_plugin("lnet_unload", lnet::unload)
        .add_plugin("lnet_start", lnet::start)
        .add_plugin("lnet_stop", lnet::stop)
        .add_plugin("lnet_configure", lnet::configure)
        .add_plugin("lnet_unconfigure", lnet::unconfigure)
        .add_plugin("ostpool_create", ostpool::action_pool_create)
        .add_plugin("ostpool_wait", ostpool::action_pool_wait)
        .add_plugin("ostpool_destroy", ostpool::action_pool_destroy)
        .add_plugin("ostpool_add", ostpool::action_pool_add)
        .add_plugin("ostpool_remove", ostpool::action_pool_remove)
        .add_plugin("snapshot_create", lustre::snapshot::create)
        .add_plugin("snapshot_destroy", lustre::snapshot::destroy)
        .add_plugin("snapshot_mount", lustre::snapshot::mount)
        .add_plugin("snapshot_unmount", lustre::snapshot::unmount)
        .add_plugin("postoffice_add", postoffice::route_add)
        .add_plugin("postoffice_remove", postoffice::route_remove)
        .add_plugin(
            "configure_ntp",
            action_configure::update_and_write_new_config,
        )
        .add_plugin("is_ntp_configured", is_ntp_configured::is_ntp_configured)
        .add_plugin("create_ldev_conf", ldev::create)
        // HotPools
        .add_plugin("create_lpurge_conf", lpurge::create_lpurge_conf)
        .add_plugin("create_lamigo_conf", lamigo::create_lamigo_conf)
        // Task Actions
        .add_plugin("action.mirror.extend", action_mirror::process_extend_fids)
        .add_plugin("action.mirror.resync", action_mirror::process_resync_fids)
        .add_plugin("action.mirror.split", action_mirror::process_split_fids)
        .add_plugin("action.stratagem.warning", action_warning::process_fids)
        .add_plugin("action.stratagem.purge", action_purge::process_fids)
        .add_plugin("action.stratagem.filesync", action_filesync::process_fids)
        .add_plugin("action.stratagem.cloudsync", action_cloudsync::process_fids);
    info!("Loaded the following ActionPlugins:");

    for ActionName(key) in map.keys() {
        info!("{}", key)
    }

    map
}
