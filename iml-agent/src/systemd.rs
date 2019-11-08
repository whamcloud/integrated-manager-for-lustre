// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    agent_error::{ImlAgentError, RequiredError},
    cmd::{cmd_output, cmd_output_success},
};
use iml_wire_types::{ActiveState, RunState, UnitFileState};
use std::{
    str,
    time::{Duration, Instant},
};
use tokio::timer::delay;

/// Waits for a unit to enter a certain state based on a given predicate.
async fn wait_for_state(
    time_to_wait: u32,
    unit_name: &str,
    check_fn: impl Fn((UnitFileState, ActiveState)) -> bool,
) -> Result<(), ImlAgentError> {
    for _ in 0_u32..(time_to_wait * 2) {
        let x = get_unit_states(unit_name).await?;

        if check_fn(x) {
            return Ok(());
        }

        delay(Instant::now() + Duration::from_millis(500)).await;
    }

    let x = get_run_state(unit_name.to_string()).await?;

    Err(ImlAgentError::from(RequiredError(format!(
        "{} did not move into expected state after {} seconds. Current state: {:?}",
        unit_name, time_to_wait, x
    ))))
}

fn clean_bus_output(output: &str) -> Result<&str, ImlAgentError> {
    output
        .split("\"")
        .nth(1)
        .ok_or_else(|| ImlAgentError::UnexpectedStatusError)
}

/// Dbus object path elements can only be comprised of [A-Z][a-z][0-9]_
///
/// This fn will take a unit name and return the encoded object path.
async fn get_unit_object_path(unit_name: &str) -> Result<String, ImlAgentError> {
    let output = cmd_output_success(
        "busctl",
        vec![
            "--system",
            "--no-pager",
            "call",
            "org.freedesktop.systemd1",
            "/org/freedesktop/systemd1",
            "org.freedesktop.systemd1.Manager",
            "LoadUnit",
            "s",
            unit_name,
        ],
    )
    .await?;

    let path = clean_bus_output(str::from_utf8(&output.stdout)?)?;

    Ok(path.to_string())
}

/// Given a unit, return `Result` of `(UnitFileState, ActiveState)`
async fn get_unit_states(unit_name: &str) -> Result<(UnitFileState, ActiveState), ImlAgentError> {
    let s = get_unit_object_path(unit_name).await?;

    let output = cmd_output_success(
        "busctl",
        vec![
            "--system",
            "--no-pager",
            "get-property",
            "org.freedesktop.systemd1",
            &s,
            "org.freedesktop.systemd1.Unit",
            "UnitFileState",
            "ActiveState",
        ],
    )
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
        _ => Err(ImlAgentError::from(RequiredError(format!(
            "Unknown busctl ({}) output: {:?}",
            s, output.stdout
        )))),
    }
}

/// Starts a unit
///
/// # Arguments
///
/// * `unit_name` - The unit to start
pub async fn start_unit(unit_name: String) -> Result<(), ImlAgentError> {
    let output = cmd_output_success(
        "busctl",
        vec![
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
        ],
    )
    .await?;

    tracing::debug!("start unit job for {}, {:?}", unit_name, output.stdout);

    wait_for_state(30, &unit_name, |(_, active_state)| {
        active_state == ActiveState::Active
    })
    .await
}

/// Stops a unit
///
/// # Arguments
///
/// * `unit_name` - The unit to stop
pub async fn stop_unit(unit_name: String) -> Result<(), ImlAgentError> {
    let output = cmd_output("systemctl", vec!["stop", &unit_name]).await?;

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
pub async fn enable_unit(unit_name: String) -> Result<(), ImlAgentError> {
    let output = cmd_output("systemctl", vec!["enable", &unit_name]).await?;

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
pub async fn disable_unit(unit_name: String) -> Result<(), ImlAgentError> {
    let output = cmd_output("systemctl", vec!["disable", &unit_name]).await?;

    tracing::debug!("disable unit result for {}, {:?}", unit_name, output.stdout);

    wait_for_state(30, &unit_name, |(enabled_state, _)| {
        enabled_state == UnitFileState::Disabled
    })
    .await
}

/// Given a `unit_name`, this fn wil return it's current
/// `RunState` which is computed based on the current `UnitFileState` and `ActiveState`.
///
///
/// | UnitFileState + ActiveState | RunState  |
/// |-----------------------------|-----------|
/// | disabled + inactive         | `Stopped` |
/// | enabled + inactive          | `Enabled` |
/// | disabled + active           | `Started` |
/// | enabled + active            | `Setup`   |
///
pub async fn get_run_state(unit_name: String) -> Result<RunState, ImlAgentError> {
    let x = get_unit_states(&unit_name).await?;

    Ok(match x {
        (UnitFileState::Disabled, ActiveState::Inactive) => RunState::Stopped,
        (UnitFileState::Enabled, ActiveState::Inactive) => RunState::Enabled,
        (UnitFileState::Disabled, ActiveState::Active) => RunState::Started,
        (UnitFileState::Enabled, ActiveState::Active) => RunState::Setup,
    })
}
