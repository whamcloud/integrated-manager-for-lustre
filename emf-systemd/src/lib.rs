// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

mod systemd_error;

use crate::systemd_error::RequiredError;
pub use crate::systemd_error::SystemdError;
use emf_cmd::{CheckedCommandExt, Command};
use emf_wire_types::{ActiveState, RunState, UnitFileState};
use std::{str, time::Duration};
use tokio::time::delay_for;

/// Waits for a unit to enter a certain state based on a given predicate.
async fn wait_for_state(
    time_to_wait: u32,
    unit_name: &str,
    check_fn: impl Fn((UnitFileState, ActiveState)) -> bool,
) -> Result<(), SystemdError> {
    for _ in 0_u32..(time_to_wait * 2) {
        let x = get_unit_states(unit_name).await?;

        if check_fn(x) {
            return Ok(());
        }

        delay_for(Duration::from_millis(500)).await;
    }

    let x = get_run_state(unit_name.to_string()).await?;

    Err(SystemdError::from(RequiredError(format!(
        "{} did not move into expected state after {} seconds. Current state: {:?}",
        unit_name, time_to_wait, x
    ))))
}

fn clean_bus_output(output: &str) -> Result<&str, SystemdError> {
    output
        .split('"')
        .nth(1)
        .ok_or(SystemdError::UnexpectedStatusError)
}

/// Dbus object path elements can only be comprised of [A-Z][a-z][0-9]_
///
/// This fn will take a unit name and return the encoded object path.
async fn get_unit_object_path(unit_name: &str) -> Result<String, SystemdError> {
    let output = Command::new("busctl")
        .args(&[
            "--system",
            "--no-pager",
            "call",
            "org.freedesktop.systemd1",
            "/org/freedesktop/systemd1",
            "org.freedesktop.systemd1.Manager",
            "LoadUnit",
            "s",
            unit_name,
        ])
        .checked_output()
        .await?;

    let path = clean_bus_output(str::from_utf8(&output.stdout)?)?;

    Ok(path.to_string())
}

/// Given a unit, return `Result` of `(UnitFileState, ActiveState)`
async fn get_unit_states(unit_name: &str) -> Result<(UnitFileState, ActiveState), SystemdError> {
    let s = get_unit_object_path(unit_name).await?;

    let output = Command::new("busctl")
        .args(&[
            "--system",
            "--no-pager",
            "get-property",
            "org.freedesktop.systemd1",
            &s,
            "org.freedesktop.systemd1.Unit",
            "UnitFileState",
            "ActiveState",
        ])
        .checked_output()
        .await?;

    let xs: Vec<_> = str::from_utf8(&output.stdout)?
        .lines()
        .filter_map(|o| clean_bus_output(o).ok())
        .collect();

    match xs.as_slice() {
        ["disabled", "inactive"] => Ok((UnitFileState::Disabled, ActiveState::Inactive)),
        ["enabled", "inactive"] => Ok((UnitFileState::Enabled, ActiveState::Inactive)),
        ["disabled", "active"] => Ok((UnitFileState::Disabled, ActiveState::Active)),
        ["enabled", "active"] => Ok((UnitFileState::Enabled, ActiveState::Active)),
        ["disabled", "activating"] => Ok((UnitFileState::Disabled, ActiveState::Activating)),
        ["enabled", "activating"] => Ok((UnitFileState::Enabled, ActiveState::Activating)),
        ["disabled", "failed"] => Ok((UnitFileState::Disabled, ActiveState::Failed)),
        ["enabled", "failed"] => Ok((UnitFileState::Enabled, ActiveState::Failed)),
        _ => Err(SystemdError::from(RequiredError(format!(
            "Unknown busctl ({}) output: {:?}",
            s,
            str::from_utf8(&output.stdout)
        )))),
    }
}

/// Starts a unit
///
/// # Arguments
///
/// * `unit_name` - The unit to start
pub async fn start_unit_and_wait(unit_name: String, time: u32) -> Result<(), SystemdError> {
    let output = Command::new("busctl")
        .args(&[
            "--system",
            "--no-pager",
            "call",
            "org.freedesktop.systemd1",
            "/org/freedesktop/systemd1",
            "org.freedesktop.systemd1.Manager",
            "StartUnit",
            "ss",
            &unit_name,
            "replace",
        ])
        .checked_output()
        .await?;

    tracing::debug!("start unit job for {}, {:?}", unit_name, output.stdout);

    wait_for_state(time, &unit_name, |(_, active_state)| {
        active_state == ActiveState::Active
    })
    .await
}

pub async fn start_unit(unit_name: String) -> Result<(), SystemdError> {
    start_unit_and_wait(unit_name, 30).await
}

/// Stops a unit
///
/// # Arguments
///
/// * `unit_name` - The unit to stop
pub async fn stop_unit(unit_name: String) -> Result<(), SystemdError> {
    let output = Command::new("systemctl")
        .args(&["stop", &unit_name])
        .output()
        .await?;

    tracing::debug!("stop unit result for {}, {:?}", unit_name, output.stdout);

    wait_for_state(30, &unit_name, |(_, active_state)| {
        active_state == ActiveState::Inactive
    })
    .await
}

/// Enables a unit
///
/// # Arguments
///
/// * `unit_name` - The unit to enable
pub async fn enable_unit(unit_name: String) -> Result<(), SystemdError> {
    let output = Command::new("systemctl")
        .args(&["enable", &unit_name])
        .output()
        .await?;

    tracing::debug!("enable unit result for {}, {:?}", unit_name, output.stdout);

    wait_for_state(30, &unit_name, |(enabled_state, _)| {
        enabled_state == UnitFileState::Enabled
    })
    .await
}

/// Disables a unit
///
/// # Arguments
///
/// * `unit_name` - The unit to disable
pub async fn disable_unit(unit_name: String) -> Result<(), SystemdError> {
    let output = Command::new("systemctl")
        .args(&["disable", &unit_name])
        .output()
        .await?;

    tracing::debug!("disable unit result for {}, {:?}", unit_name, output.stdout);

    wait_for_state(30, &unit_name, |(enabled_state, _)| {
        enabled_state == UnitFileState::Disabled
    })
    .await
}

/// Restarts a unit
///
/// # Arguments
///
/// * `unit_name` - The unit to restart
pub async fn restart_unit(unit_name: String) -> Result<(), SystemdError> {
    let output = Command::new("systemctl")
        .args(&["restart", &unit_name])
        .output()
        .await?;

    tracing::debug!("restart unit result for {}, {:?}", unit_name, output.stdout);

    wait_for_state(30, &unit_name, |(_, active_state)| {
        active_state == ActiveState::Active
    })
    .await
}

/// Given a `unit_name`, this fn wil return it's current
/// `RunState` which is computed based on the current `UnitFileState` and `ActiveState`.
///
///
/// | UnitFileState + ActiveState | RunState     |
/// |-----------------------------|--------------|
/// | disabled + inactive         | `Stopped`    |
/// | enabled + inactive          | `Enabled`    |
/// | disabled + active           | `Started`    |
/// | enabled + active            | `Setup`      |
/// | disabled + activating       | `Activating` |
/// | enabled + activating        | `Activating` |
///
pub async fn get_run_state(unit_name: String) -> Result<RunState, SystemdError> {
    let x = get_unit_states(&unit_name).await?;

    Ok(match x {
        (UnitFileState::Disabled, ActiveState::Inactive) => RunState::Stopped,
        (UnitFileState::Enabled, ActiveState::Inactive) => RunState::Enabled,
        (UnitFileState::Disabled, ActiveState::Active) => RunState::Started,
        (UnitFileState::Enabled, ActiveState::Active) => RunState::Setup,
        (UnitFileState::Disabled, ActiveState::Activating) => RunState::Activating,
        (UnitFileState::Enabled, ActiveState::Activating) => RunState::Activating,
        (UnitFileState::Disabled, ActiveState::Failed) => RunState::Failed,
        (UnitFileState::Enabled, ActiveState::Failed) => RunState::Failed,
    })
}
