// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::agent_error::ImlAgentError;
use iml_cmd::{CheckedCommandExt, Command};
use lazy_static::lazy_static;
use regex::Regex;
use std::{collections::HashMap, convert::TryFrom, io};
use tokio::{fs::OpenOptions, io::AsyncWriteExt};

static COROSYNC_CONF: &str = "/etc/corosync/corosync.conf";

/// Reads the corosync configuration.
async fn read_corosync_conf() -> Result<Vec<u8>, io::Error> {
    iml_fs::read_file_to_end(COROSYNC_CONF).await
}

/// Truncates and writes a new configuration.
async fn write_corosync_conf(xs: &[u8]) -> Result<(), ImlAgentError> {
    OpenOptions::new()
        .write(true)
        .truncate(true)
        .open(COROSYNC_CONF)
        .await?
        .write_all(xs)
        .await?;

    Ok(())
}

/// Updates the config_version. This is useful so nodes can tell which conf is newer.
fn update_config_version(
    s: impl Iterator<Item = String>,
    next_version: u64,
) -> impl Iterator<Item = String> {
    s.filter(|x| !x.trim().starts_with("config_version:"))
        .map(move |x| {
            if x.trim().starts_with("version:") {
                format!("{}\n    config_version: {}", x, next_version)
            } else {
                x
            }
        })
}

/// Updates the mcastport for all interfaces in the corosync.conf.
fn update_mcast_port(
    s: impl Iterator<Item = String>,
    new_port: u16,
) -> impl Iterator<Item = String> {
    lazy_static! {
        static ref RE: Regex = Regex::new(r"(\s*mcastport:\s*)\d+").unwrap();
    }

    s.map(move |x| {
        if x.trim().starts_with("mcastport:") {
            RE.replace(&x, |caps: &regex::Captures| {
                format!("{}{}", &caps[1], new_port)
            })
            .to_string()
        } else {
            x
        }
    })
}

/// Given a new mcast port, updates the port on each interface,
/// bumps the config_version and writes out the new corosync.conf.
pub(crate) async fn change_mcast_port(new_port: u16) -> Result<(), ImlAgentError> {
    let conf = read_corosync_conf().await?;
    let conf = std::str::from_utf8(&conf)?
        .trim()
        .lines()
        .map(|x| x.to_string());

    let (totem, _) = corosync_cmapctl().await?;

    let conf = update_config_version(conf, totem.next_version());
    let conf = update_mcast_port(conf, new_port);
    let conf = conf.collect::<Vec<_>>().join("\n");

    write_corosync_conf(conf.as_bytes()).await?;

    Ok(())
}

type StringMap<'a> = HashMap<&'a str, &'a str>;

#[derive(Debug)]
pub(crate) struct Totem {
    config_version: Option<u64>,
    cluster_name: String,
    token: u32,
}

impl Totem {
    fn next_version(&self) -> u64 {
        match self.config_version {
            Some(x) => x + 1,
            None => 1,
        }
    }
}

impl<'a> TryFrom<&'a StringMap<'a>> for Totem {
    type Error = ImlAgentError;

    fn try_from(x: &'a StringMap<'a>) -> Result<Self, Self::Error> {
        Ok(Totem {
            config_version: x
                .get("config_version (u64)")
                .map(|x| x.parse())
                .transpose()?,
            cluster_name: (*try_get(x, "cluster_name (str)")?).to_string(),
            token: try_get(x, "token (u32)")?.parse()?,
        })
    }
}

#[derive(Debug, Eq, PartialEq, Ord, PartialOrd)]
pub(crate) struct Interface {
    ringnumber: u32,
    bindnetaddr: String,
    mcastaddr: Option<String>,
    broadcast: Option<String>,
    mcastport: u16,
}

impl<'a> TryFrom<(&'a str, StringMap<'a>)> for Interface {
    type Error = ImlAgentError;

    fn try_from((ringnumber, x): (&'a str, StringMap<'a>)) -> Result<Self, Self::Error> {
        Ok(Interface {
            ringnumber: ringnumber.parse()?,
            bindnetaddr: (*try_get(&x, "bindnetaddr (str)")?).to_string(),
            mcastaddr: x.get("mcastaddr (str)").map(|x| (*x).to_string()),
            broadcast: x.get("broadcast (str)").map(|x| (*x).to_string()),
            mcastport: try_get(&x, "mcastport (u16)")?.parse()?,
        })
    }
}

/// View the current totem and interface information from `corosync-cmapctl`.
async fn corosync_cmapctl() -> Result<(Totem, Vec<Interface>), ImlAgentError> {
    let x = Command::new("corosync-cmapctl")
        .arg("totem")
        .kill_on_drop(true)
        .checked_output()
        .await?;

    corosync_cmapctl_parser(&x.stdout)
}

fn corosync_cmapctl_parser(x: &[u8]) -> Result<(Totem, Vec<Interface>), ImlAgentError> {
    let x = std::str::from_utf8(x)?;

    let (totem, interfaces) = x
        .trim()
        .lines()
        .filter_map(|y| {
            let xs: Vec<_> = y.split('=').collect();

            match xs[..] {
                [k, v] => Some((k.trim(), v.trim())),
                _ => None,
            }
        })
        .map(|(k, v)| (k.split('.').collect(), v))
        .fold(
            (HashMap::new(), HashMap::new()),
            |(mut totem, mut interfaces): (StringMap, HashMap<&str, StringMap>),
             (k, v): (Vec<_>, _)| {
                match k[..] {
                    ["totem", y] => {
                        totem.insert(y, v);
                    }
                    ["totem", "interface", x, y] => {
                        interfaces.entry(x).or_default().insert(y, v);
                    }

                    _ => {}
                }

                (totem, interfaces)
            },
        );

    Ok((
        Totem::try_from(&totem)?,
        interfaces
            .into_iter()
            .map(Interface::try_from)
            .collect::<Result<_, _>>()?,
    ))
}

fn try_get<'a>(hm: &'a StringMap<'a>, k: &str) -> Result<&'a &'a str, ImlAgentError> {
    hm.get(k)
        .ok_or_else(|| io::Error::new(io::ErrorKind::NotFound, format!("Property {} not found", k)))
        .map_err(|e| e.into())
}

#[cfg(test)]
mod tests {
    use super::{corosync_cmapctl_parser, update_config_version, update_mcast_port};
    use std::iter::FromIterator;

    fn corosync_cmapctl_fixture() -> &'static [u8] {
        include_bytes!("../fixtures/corosync-cmapctl-totem.txt")
    }

    fn corosync_conf_fixture() -> &'static [u8] {
        include_bytes!("../fixtures/corosync.conf")
    }

    #[test]
    fn test_corosync_cmapctl_output() -> Result<(), Box<dyn std::error::Error>> {
        let x = corosync_cmapctl_fixture();

        let mut y = corosync_cmapctl_parser(x)?;

        y.1.sort_unstable();

        insta::assert_debug_snapshot!(y);

        Ok(())
    }

    #[test]
    fn test_update_config_version() -> Result<(), Box<dyn std::error::Error>> {
        let conf = corosync_conf_fixture();

        let conf = std::str::from_utf8(&conf)?
            .trim()
            .lines()
            .map(|x| x.to_string());

        let conf = Vec::from_iter(update_config_version(conf, 10)).join("\n");

        insta::assert_display_snapshot!(conf);

        Ok(())
    }

    #[test]
    fn test_update_mcast_port() -> Result<(), Box<dyn std::error::Error>> {
        let conf = corosync_conf_fixture();

        let conf = std::str::from_utf8(&conf)?
            .trim()
            .lines()
            .map(|x| x.to_string());

        let conf = Vec::from_iter(update_mcast_port(conf, 40001)).join("\n");

        insta::assert_display_snapshot!(conf);

        Ok(())
    }
}
