// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::ImlAgentError, cmd::cmd_output, cmd::cmd_output_success};
use std::cmp::Ordering;

#[derive(Debug, PartialEq, Eq)]
enum VerPart {
    Int(u32),
    Str(String),
}

impl Ord for VerPart {
    fn cmp(&self, other: &Self) -> Ordering {
        match (self, other) {
            (VerPart::Int(s), VerPart::Int(o)) => s.cmp(o),
            (VerPart::Int(_), VerPart::Str(_)) => Ordering::Greater,
            (VerPart::Str(_), VerPart::Int(_)) => Ordering::Less,
            (VerPart::Str(s), VerPart::Str(o)) => s.cmp(o),
        }
    }
}

impl PartialOrd for VerPart {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl From<String> for VerPart {
    fn from(part: String) -> Self {
        match part.parse::<u32>() {
            Ok(n) => VerPart::Int(n),
            Err(_) => VerPart::Str(part),
        }
    }
}

impl From<&str> for VerPart {
    fn from(part: &str) -> Self {
        match part.parse::<u32>() {
            Ok(n) => VerPart::Int(n),
            Err(_) => VerPart::Str(part.to_string()),
        }
    }
}

#[derive(Debug, Eq)]
struct Version {
    version: String,
    v: Vec<VerPart>,
    r: Vec<VerPart>,
}

impl From<&str> for Version {
    fn from(version: &str) -> Self {
        let vr: Vec<&str> = version.splitn(2, '-').collect();
        Version {
            version: version.to_string(),
            v: if vr.len() > 0 {
                vr[0].split('.').map(|s| VerPart::from(s)).collect()
            } else {
                vec![]
            },
            r: if vr.len() > 1 {
                vr[1].split('.').map(|s| VerPart::from(s)).collect()
            } else {
                vec![]
            },
        }
    }
}

impl Ord for Version {
    fn cmp(&self, other: &Self) -> Ordering {
        self.v.cmp(&other.v).then(self.r.cmp(&other.r))
    }
}
impl PartialOrd for Version {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl PartialEq for Version {
    fn eq(&self, other: &Self) -> bool {
        self.version == other.version
    }
}

async fn check_kver_module(module: &str, kver: &str) -> Result<bool, ImlAgentError> {
    let output = cmd_output("modinfo", vec!["-n", "-k", kver, module])
        .await?;

    Ok(output.status.success())
}

pub async fn get_kernel(modules: Vec<String>) -> Result<String, ImlAgentError> {
    let output = cmd_output_success("rpm", vec!["-q", "--qf", "%{V}-%{R}.%{ARCH}\n", "kernel"])
        .await?;

    let mut newest = Version::from("");

    for kver in std::str::from_utf8(output.stdout.as_slice())?.lines() {
        let contender = Version::from(kver);
        if contender <= newest {
            continue;
        }
        let mut okay = true;
        for module in modules.iter() {
            if !check_kver_module(&module, kver).await? {
                okay = false;
                break;
            }
        }
        if okay {
            newest = contender;
        }
    }
    Ok(newest.version)
}
