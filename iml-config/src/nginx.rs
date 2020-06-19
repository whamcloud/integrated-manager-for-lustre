// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::error::ImlConfigError;
use console::Term;
use std::{env, str};
use structopt::StructOpt;
use tokio::fs;

#[derive(Debug, StructOpt)]
pub enum NginxCommand {
    /// Generate Nginx conf
    #[structopt(name = "generate-config")]
    GenerateConfig {
        /// Set the nginx config path
        #[structopt(short = "p", long = "path")]
        template_path: String,

        #[structopt(short = "o", long = "output")]
        output_path: Option<String>,
    },
}

const TEMPLATE_VARS: &[&str] = &[
    "REPO_PATH",
    "HTTP_FRONTEND_PORT",
    "HTTPS_FRONTEND_PORT",
    "HTTP_AGENT_PROXY_PASS",
    "HTTP_AGENT2_PROXY_PASS",
    "HTTP_API_PROXY_PASS",
    "IML_API_PROXY_PASS",
    "WARP_DRIVE_PROXY_PASS",
    "MAILBOX_PATH",
    "MAILBOX_PROXY_PASS",
    "SSL_PATH",
    "DEVICE_AGGREGATOR_PORT",
    "DEVICE_AGGREGATOR_PROXY_PASS",
    "UPDATE_HANDLER_PROXY_PASS",
    "GRAFANA_PORT",
    "GRAFANA_PROXY_PASS",
    "INFLUXDB_PROXY_PASS",
    "TIMER_PROXY_PASS",
    "INCLUDES",
];

fn replace_template_variables(contents: &str, template_vars: &[&str]) -> String {
    let mut updated_contents: String = contents.to_string();
    for var in template_vars {
        updated_contents = updated_contents.replace(
            // find a better way to do this
            &format!("{{{{{}}}}}", var),
            &env::var(var).unwrap_or_else(|_| panic!("{} variable not set", var)),
        );
    }

    updated_contents
}

pub async fn nginx_cli(command: NginxCommand) -> Result<(), ImlConfigError> {
    match command {
        NginxCommand::GenerateConfig {
            template_path,
            output_path,
        } => {
            let nginx_template_bytes = fs::read(template_path).await?;
            let nginx_template = String::from_utf8(nginx_template_bytes)?;

            let config = replace_template_variables(&nginx_template, TEMPLATE_VARS);

            if let Some(path) = output_path {
                fs::write(path, config).await?;
            } else {
                let term = Term::stdout();

                tracing::debug!("Nginx Config: {}", config);

                term.write_line(&config).unwrap();
            }
        }
    };

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use insta::*;

    fn clear_env_vars(vars: &[&str]) {
        for key in vars {
            env::remove_var(key);
        }
    }

    #[test]
    fn test_replace_template_variables() {
        let template: &[u8] = include_bytes!("../../chroma-manager.conf.template");

        clear_env_vars(TEMPLATE_VARS);

        env::set_var("REPO_PATH", "/var/lib/chroma/repo");
        env::set_var("HTTP_FRONTEND_PORT", "80");
        env::set_var("HTTPS_FRONTEND_PORT", "443");
        env::set_var("HTTP_AGENT_PROXY_PASS", "http://127.0.0.1:8002");
        env::set_var("HTTP_AGENT2_PROXY_PASS", "http://127.0.0.1:8003");
        env::set_var("HTTP_API_PROXY_PASS", "http://127.0.0.1:8001");
        env::set_var("IML_API_PROXY_PASS", "http://127.0.0.1:8004");
        env::set_var("WARP_DRIVE_PROXY_PASS", "http://127.0.0.1:8890");
        env::set_var("MAILBOX_PATH", "/var/spool/iml/mailbox");
        env::set_var("MAILBOX_PROXY_PASS", "http://127.0.0.1:8891");
        env::set_var("SSL_PATH", "/var/lib/chroma");
        env::set_var("DEVICE_AGGREGATOR_PORT", "8008");
        env::set_var("DEVICE_AGGREGATOR_PROXY_PASS", "http://127.0.0.1:8008");
        env::set_var(
            "UPDATE_HANDLER_PROXY_PASS",
            "http://unix:/var/run/iml-update-handler.sock",
        );
        env::set_var("GRAFANA_PORT", "3000");
        env::set_var("GRAFANA_PROXY_PASS", "http://127.0.0.1:3000");
        env::set_var("INFLUXDB_PROXY_PASS", "http://127.0.0.1:8086");
        env::set_var("TIMER_PROXY_PASS", "http://127.0.0.1:8892");
        env::set_var("INCLUDES", "");

        let config = replace_template_variables(
            &str::from_utf8(template).expect("Couldn't parse template"),
            TEMPLATE_VARS,
        );

        assert_display_snapshot!(config);
    }
}
