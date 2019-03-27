// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use dns_lookup;
use lazy_static::lazy_static;
use std::fs::File;
use std::io::{BufRead, BufReader};
use std::net::ToSocketAddrs;

/// Gets the hostname for the node or panics
lazy_static! {
    pub static ref HOSTNAME: std::net::SocketAddr = {
        let host = dns_lookup::get_hostname().expect("Could not lookup hostname");

        (host.as_str(), 0)
            .to_socket_addrs()
            .expect("Could not convert host to SocketAddr")
            .next()
            .expect("Could not get SocketAddr from hostname")
    };
}

/// Gets the FQDN or panics
lazy_static! {
    pub static ref FQDN: String = dns_lookup::getnameinfo(&HOSTNAME, 0)
        .map(|(x, _)| x)
        .unwrap();
}

/// Gets the server boot time or panics.
lazy_static! {
    pub static ref BOOT_TIME: String = {
        let input = File::open("/proc/stat").expect("Could not open /proc/stat");
        let buffered = BufReader::new(input);

        let lines = buffered
            .lines()
            .collect::<std::result::Result<Vec<String>, _>>()
            .expect("Error reading lines from /proc/stat");

        let secs = lines
            .iter()
            .map(|l| l.split_whitespace().collect())
            .filter_map(|xs: Vec<&str>| match xs[..2] {
                ["btime", v] => Some(v),
                _ => None,
            })
            .nth(0)
            .expect("Could not find boot time")
            .parse()
            .expect("Could not parse boot secs into int");

        chrono::NaiveDateTime::from_timestamp(secs, 0)
            .format("%Y-%m-%dT%T.%6f+00:00Z")
            .to_string()
    };
}
