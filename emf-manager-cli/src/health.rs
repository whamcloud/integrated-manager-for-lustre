// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{display_utils::display_success, error::EmfManagerCliError};
use emf_manager_client::{create_url, get_client};
use emf_request_retry::{policy::exponential_backoff_policy_builder, retry_future};
use kuma_client::ServiceInsight;
use std::collections::HashMap;
use structopt::StructOpt;

#[derive(Debug, StructOpt)]
#[structopt(setting = structopt::clap::AppSettings::ColoredHelp)]
pub enum Command {
    /// Show manager health
    #[structopt(name = "manager")]
    Manager,
}

static MANAGER_SERVICES: [&'static str; 14] = [
    "emf-api-service",
    "emf-device-service",
    "emf-host-service",
    "emf-journal-service",
    "emf-network-service",
    "emf-ntp-service",
    "emf-ostpool-service",
    "emf-corosync-service",
    "emf-stats-service",
    "emf-state-machine-service",
    "emf-warp-drive-service",
    "postgres",
    "grafana",
    "influx",
];

pub async fn cli(command: Option<Command>) -> Result<(), EmfManagerCliError> {
    let command = command.unwrap_or(Command::Manager);

    match command {
        Command::Manager => {
            let client = kuma_client::create(get_client()?, create_url("kuma/")?);

            let policy = exponential_backoff_policy_builder().build();

            let xs = retry_future(|_| client.service_insights(), policy)
                .await?
                .items;

            let x = parse_service_health(xs);

            println!("Manager service mesh status\n");

            let failed = x.values().any(|x| x != "online");

            for (name, status) in x {
                println!("{}: {}", name, status);
            }

            println!("");

            if failed {
                return Err(EmfManagerCliError::StateError(
                    "Services offline".to_string(),
                ));
            }

            display_success("Services online");
        }
    };

    Ok(())
}

fn parse_service_health(xs: Vec<ServiceInsight>) -> HashMap<&'static str, String> {
    let mut x: HashMap<String, String> = xs.into_iter().map(|x| (x.name, x.status)).collect();

    MANAGER_SERVICES
        .iter()
        .map(|name| {
            (
                *name,
                x.remove(*name).unwrap_or_else(|| "unknown".to_string()),
            )
        })
        .collect()
}

#[cfg(test)]
mod test {
    use super::*;
    use kuma_client::List;

    #[test]
    fn test_service_health() {
        let fixture = include_bytes!("../fixtures/kuma-service-insights.json");

        let xs: List<ServiceInsight> = serde_json::from_slice(fixture).unwrap();

        let xs = parse_service_health(xs.items);

        insta::with_settings!({sort_maps => true}, {
            insta::assert_json_snapshot!(xs);
        });
    }
}
