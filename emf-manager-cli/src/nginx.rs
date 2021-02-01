// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{display_utils::display_success, error::EmfManagerCliError};
use console::Term;
use emf_cmd::{CheckedCommandExt as _, Command, OutputExt as _};
use emf_fs::mkdirp;
use lazy_static::lazy_static;
use regex::{Captures, Regex};
use std::{collections::HashMap, env, path::PathBuf, process::Stdio, str};
use structopt::StructOpt;
use tokio::fs;

#[derive(Debug, StructOpt)]
#[structopt(setting = structopt::clap::AppSettings::ColoredHelp)]
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
    /// Generate self-signed certificates.
    #[structopt(name = "generate-self-certs")]
    GenerateSelfSignedCerts {
        /// Certificate output directory
        #[structopt(long, env = "NGINX_CRYPTO_DIR", parse(from_os_str))]
        out: PathBuf,
        /// How many days should the certificate be valid for?
        #[structopt(long, env = "NGINX_CERT_EXPIRE_DAYS")]
        days: u32,
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

fn openssl() -> Command {
    emf_cmd::Command::new("/usr/bin/openssl")
}

pub async fn nginx_cli(command: NginxCommand) -> Result<(), EmfManagerCliError> {
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

                emf_tracing::tracing::debug!(%config);

                term.write_line(&config).unwrap();
            }
        }
        NginxCommand::GenerateSelfSignedCerts { out, days } => {
            println!("Generating self-signed certs...");

            if !emf_fs::dir_exists(&out).await {
                mkdirp(&out).await?;
            }

            let cert_path = out.join("ca.crt");

            if emf_fs::file_exists(&cert_path).await {
                println!("Certificate already exists. If you'd like to regenerate certificates, delete {:?} and try again.", &cert_path);
                return Ok(());
            }

            let fqdn = emf_cmd::Command::new("hostname")
                .arg("-f")
                .checked_output()
                .await?;
            let fqdn = fqdn.try_stdout_str()?.trim();

            tracing::debug!(%fqdn);

            let conf = format!(
                r#"
[ req ]
distinguished_name = req_distinguished_name
req_extensions = v3_req
x509_extensions = v3_req
prompt = no

[ req_distinguished_name ]
CN = {fqdn}

[ v3_req ]
# Extensions to add to a certificate request
subjectKeyIdentifier = hash
basicConstraints = critical,CA:false
keyUsage = critical,digitalSignature,keyEncipherment
subjectAltName = DNS:{fqdn}
"#,
                fqdn = fqdn
            );

            let cfg_path = emf_fs::write_tempfile(conf.as_bytes().to_vec()).await?;

            let ca_key_path = out.join("ca.key");

            if !emf_fs::file_exists(&ca_key_path).await {
                openssl()
                    .stderr(Stdio::null())
                    .stdout(Stdio::null())
                    .arg("genrsa")
                    .arg("-out")
                    .arg(&ca_key_path)
                    .arg("2048")
                    .checked_status()
                    .await?;
            }

            let csr = openssl()
                .stderr(Stdio::null())
                .arg("req")
                .arg("-new")
                .arg("-sha256")
                .arg("-key")
                .arg(&ca_key_path)
                .arg("-config")
                .arg(cfg_path.path())
                .checked_output()
                .await?;
            let csr = csr.try_stdout_str()?;
            let csr_path = emf_fs::write_tempfile(csr.as_bytes().to_vec()).await?;

            openssl()
                .stdout(Stdio::null())
                .stderr(Stdio::null())
                .arg("x509")
                .arg("-req")
                .arg("-sha256")
                .arg("-days")
                .arg(days.to_string())
                .arg("-extfile")
                .arg(cfg_path.path())
                .arg("-extensions")
                .arg("v3_req")
                .arg("-in")
                .arg(csr_path.path())
                .arg("-signkey")
                .arg(&ca_key_path)
                .arg("-out")
                .arg(&cert_path)
                .checked_status()
                .await?;

            display_success(format!("Nginx Certs written to {:?}", out));
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
            ("EMF_API_PROXY_PASS", "http://127.0.0.1:8004"),
            ("WARP_DRIVE_PROXY_PASS", "http://127.0.0.1:8890"),
            ("MAILBOX_PROXY_PASS", "http://127.0.0.1:8891"),
            ("SSL_PATH", "/var/lib/chroma"),
            ("DEVICE_AGGREGATOR_PORT", "8008"),
            ("DEVICE_AGGREGATOR_PROXY_PASS", "http://127.0.0.1:8008"),
            ("GRAFANA_PORT", "3000"),
            ("GRAFANA_PROXY_PASS", "http://127.0.0.1:3000"),
            ("INFLUXDB_PROXY_PASS", "http://127.0.0.1:8086"),
            ("REPORT_PATH", "/var/spool/emf/report"),
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
