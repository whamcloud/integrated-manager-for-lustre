// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::error::ImlConfigError;
use console::Term;
use lazy_static::*;
use regex::{Captures, Regex};
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

fn get_var_value(key: &str) -> String {
    env::var(key).unwrap_or_else(|_| panic!("{} variable not set", key))
}

fn replace_template_variables(contents: &str, get_var_value: fn(&str) -> String) -> String {
    lazy_static! {
        static ref RE: Regex = Regex::new(r"^.*\{\{(?P<template_var>.*)\}\}.*$").unwrap();
    }

    let config: String = contents
        .lines()
        .map(|l| {
            RE.replace(l, |caps: &Captures| {
                let key = &caps[1];
                let val = get_var_value(key);
                l.replace(&format!("{{{{{}}}}}", key), &val)
            })
            .to_string()
        })
        .collect::<Vec<String>>()
        .join("\n");

    config
}

pub async fn nginx_cli(command: NginxCommand) -> Result<(), ImlConfigError> {
    match command {
        NginxCommand::GenerateConfig {
            template_path,
            output_path,
        } => {
            let nginx_template_bytes = fs::read(template_path).await?;
            let nginx_template = String::from_utf8(nginx_template_bytes)?;

            let config = replace_template_variables(&nginx_template, get_var_value);

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
    use std::collections::HashMap;

    fn get_var_value(key: &str) -> String {
        let template_vars = [
            ("REPO_PATH", "/var/lib/chroma/repo"),
            ("HTTP_FRONTEND_PORT", "80"),
            ("HTTPS_FRONTEND_PORT", "443"),
            ("HTTP_AGENT_PROXY_PASS", "http://127.0.0.1:8002"),
            ("HTTP_AGENT2_PROXY_PASS", "http://127.0.0.1:8003"),
            ("HTTP_API_PROXY_PASS", "http://127.0.0.1:8001"),
            ("IML_API_PROXY_PASS", "http://127.0.0.1:8004"),
            ("WARP_DRIVE_PROXY_PASS", "http://127.0.0.1:8890"),
            ("MAILBOX_PATH", "/var/spool/iml/mailbox"),
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
            ("TIMER_PROXY_PASS", "http://127.0.0.1:8892"),
            ("INCLUDES", ""),
        ]
        .iter()
        .cloned()
        .collect::<HashMap<&str, &str>>();

        template_vars
            .get(key)
            .unwrap_or_else(|| {
                panic!("Variable {} not found!", key);
            })
            .to_string()
    }

    #[test]
    fn test_replace_template_variables() {
        let template: &[u8] = include_bytes!("../../chroma-manager.conf.template");

        let config = replace_template_variables(
            &str::from_utf8(template).expect("Couldn't parse template"),
            get_var_value,
        );

        assert_display_snapshot!(config);
    }
}
