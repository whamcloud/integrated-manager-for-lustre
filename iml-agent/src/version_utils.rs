// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use std::cmp::Ordering;
use std::fmt;

#[derive(Debug, PartialEq, Eq)]
pub enum VerPart {
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
pub struct Version {
    pub version: String,
    pub v: Vec<VerPart>,
    pub r: Vec<VerPart>,
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

impl fmt::Display for Version {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "{}", self.version)
    }
}

#[cfg(test)]
mod tests {
    use super::Version;

    #[test]
    fn test_version_eq() {
        assert_eq!(Version::from("1.0"), Version::from("1.0"));
        assert_eq!(Version::from("1.0"), Version::from("1.00"));
        assert_eq!(Version::from("1.0-1.1"), Version::from("1.00-1.01"));
    }

    #[test]
    fn test_version_cmp() {
        assert!(Version::from("1.0") > Version::from("1"));
        assert!(Version::from("1.1") > Version::from("1.00"));
    }

    #[test]
    fn test_version_display() {
        let version = "1.3-5.0".to_string();
        let ver = Version::from(ver);
        
        assert_eq!(version, format!("{}", ver));
    }
}
