// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::agent_error::ImlAgentError;
use futures::future::{try_join_all, FutureExt as _};

use iml_cmd::{CheckedCommandExt, Command};
use iml_tracing::tracing;

/// For information on LNet operations see: https://wiki.lustre.org/Starting_and_Stopping_LNet

// Ensures that each command calls `kill_on_drop`.
fn command(command: &str, args: &[&str]) -> Command {
    let mut cmd = Command::new(command);
    cmd.args(args).kill_on_drop(true);

    cmd
}

/// Load the LNet modules from disk into memory, including any modules using the modprobe command.
pub async fn load(_args: Vec<String>) -> Result<(), ImlAgentError> {
    command("modprobe", &["lnet"])
        .checked_status()
        .inspect(|x| match x {
            Ok(_) => tracing::debug!("Load LNet: Successfully loaded LNet."),
            Err(e) => tracing::debug!(
                "Load LNet: Error encountered: `modprobe lnet` failed. {:?}",
                e
            ),
        })
        .await?;

    Ok(())
}

/// Unload the LNet modules from memory, including any modules that are dependent on the LNet
/// module. LNet must be stopped before this function is called.
pub async fn unload(_args: Vec<String>) -> Result<(), ImlAgentError> {
    command("lustre_rmmod", &[])
        .checked_status()
        .inspect(|x| match x {
            Ok(_) => tracing::debug!("Unload LNet: Successfully unloaded LNet."),
            Err(e) => tracing::debug!(
                "Unload LNet: Error encountered: `lustre_rmmod` failed. {:?}",
                e
            ),
        })
        .await?;

    Ok(())
}

/// Place LNet into the `up` state.
pub async fn start(_args: Vec<String>) -> Result<(), ImlAgentError> {
    command("lnetctl", &["lnet", "configure", "--all"])
        .checked_status()
        .inspect(|x| match x {
            Ok(_) => tracing::debug!("Start LNet: Successfully started LNet."),
            Err(e) => tracing::debug!(
                "Start LNet: Error encountered: `lnetctl lnet configure --all` failed. {:?}",
                e
            ),
        })
        .await?;

    Ok(())
}

/// Place LNet into the `down` state. Any modules that are dependent on LNet being in the `up` state
/// will be unloaded before LNet is stopped.
pub async fn stop(_args: Vec<String>) -> Result<(), ImlAgentError> {
    command("lustre_rmmod", &["ptlrpc"])
        .checked_status()
        .inspect(|x| match x {
            Ok(_) => tracing::debug!("Stop LNet: Step 1 completed."),
            Err(e) => tracing::debug!(
                "Stop LNet: Error encountered during step 1: `lustre_rmmod ptlrpc` failed. {:?}",
                e
            ),
        })
        .await?;

    command("lnetctl", &["lnet", "unconfigure"])
        .checked_status()
        .inspect(|x| {
            match x {
                Ok(_) => tracing::debug!("Stop LNet: Step 2 completed. Sucessfully stopped LNet."),
                Err(e) => tracing::debug!("Stop LNet: Error encountered during step 2: `lnetctl lnet unconfigure` failed. {:?}", e),
            }
        })
        .await?;

    Ok(())
}

/// Configure LNet using the nids
pub async fn configure(interfaces: Vec<(String, String)>) -> Result<(), ImlAgentError> {
    let xs = interfaces
        .into_iter()
        .map(|(net, iface)| async move {
            command("lnetctl", &["net", "add", "--net", &net, "--if", &iface])
                .checked_status()
                .inspect(|x| {
                    match x {
                        Ok(_) => tracing::debug!("Configure LNet: Successfully configured LNet using network {} and interface {}.", net, iface),
                        Err(e) => tracing::debug!("Configure LNet: Error encountered: `lnetctl net add --net {} --if {}` failed. {:?}", net, iface, e),
                    }
                })
                .await
        });

    try_join_all(xs).await?;

    Ok(())
}

/// Unconfigure LNet
pub async fn unconfigure(interfaces: Vec<String>) -> Result<(), ImlAgentError> {
    let xs = interfaces.into_iter().map(|net| async move {
        command("lnetctl", &["net", "del", "--net", &net])
            .checked_status()
            .inspect(|x| match x {
                Ok(_) => tracing::debug!(
                    "Unconfigure LNet: Successfully unconfigured LNet using network {}.",
                    net
                ),
                Err(e) => tracing::debug!(
                    "Unconfigure LNet: Error encountered: `lnetctl net del --net {}` failed. {:?}",
                    net,
                    e
                ),
            })
            .await
    });

    try_join_all(xs).await?;

    Ok(())
}
