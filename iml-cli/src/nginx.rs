// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::error::ImlManagerCliError;
use console::Term;
use lazy_static::*;
use regex::{Captures, Regex};
use std::{collections::HashMap, env, str};
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

fn replace_template_variables(contents: &str, vars: HashMap<String, String>) -> String {
    lazy_static! {
        static ref RE: Regex = Regex::new(r"(\{\{\w+\}\})").unwrap();
    }

    let config: String = contents
        .lines()
        .map(|l| {
            RE.replace_all(l, |caps: &Captures| {
                let key = &caps[1].replace("{", "").replace("}", "");
                let val = vars
                    .get(key)
                    .unwrap_or_else(|| panic!("{} variable not set", key));

                caps[0].replace(&caps[1], &val)
            })
            .to_string()
        })
        .collect::<Vec<String>>()
        .join("\n");

    config
}

pub async fn nginx_cli(command: NginxCommand) -> Result<(), ImlManagerCliError> {
    match command {
        NginxCommand::GenerateConfig {
            template_path,
            output_path,
        } => {
            let nginx_template_bytes = fs::read(template_path).await?;
            let nginx_template = String::from_utf8(nginx_template_bytes)?;

            let vars: HashMap<String, String> = env::vars().collect();

            let config = replace_template_variables(&nginx_template, vars);

            if let Some(path) = output_path {
                fs::write(path, config).await?;
            } else {
                let term = Term::stdout();

                iml_tracing::tracing::debug!("Nginx Config: {}", config);

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
    use std::collections::HashMap;

    #[test]
    fn test_replace_template_variables() {
        let template: &[u8] = include_bytes!("../../chroma-manager.conf.template");

        let vars: HashMap<String, String> = [
            ("REPO_PATH", "/var/lib/chroma/repo"),
            ("HTTP_FRONTEND_PORT", "80"),
            ("HTTPS_FRONTEND_PORT", "443"),
            ("HTTP_AGENT_PROXY_PASS", "http://127.0.0.1:8002"),
            ("HTTP_AGENT2_PROXY_PASS", "http://127.0.0.1:8003"),
            ("HTTP_API_PROXY_PASS", "http://127.0.0.1:8001"),
            ("IML_API_PROXY_PASS", "http://127.0.0.1:8004"),
            ("WARP_DRIVE_PROXY_PASS", "http://127.0.0.1:8890"),
            ("MAILBOX_PROXY_PASS", "http://127.0.0.1:8891"),
            ("SSL_PATH", "/var/lib/chroma"),
            ("DEVICE_AGGREGATOR_PORT", "8008"),
            ("DEVICE_AGGREGATOR_PROXY_PASS", "http://127.0.0.1:8008"),
            (
                "UPDATE_HANDLER_PROXY_PASS",
                "http://unix:/var/run/iml-update-handler.sock",
            ),
            ("GRAFANA_PORT", "3000"),
            ("GRAFANA_PROXY_PASS", "http://127.0.0.1:3000"),
            ("INFLUXDB_PROXY_PASS", "http://127.0.0.1:8086"),
            ("REPORT_PATH", "/var/spool/iml/report"),
            ("REPORT_PROXY_PASS", "http://127.0.0.1:8893"),
        ]
        .iter()
        .map(|(k, v)| (k.to_string(), v.to_string()))
        .collect();

        let config = replace_template_variables(
            &str::from_utf8(template).expect("Couldn't parse template"),
            vars,
        );

        assert_display_snapshot!(config);
    }

    #[test]
    fn test_multiple_replacements() {
        let vars: HashMap<String, String> = [("FOO", "foo"), ("BAR", "bar")]
            .iter()
            .map(|(k, v)| (k.to_string(), v.to_string()))
            .collect();

        let cfg = replace_template_variables("{{FOO}}/{{BAR}}", vars);

        assert_eq!(cfg, "foo/bar");
    }
}
