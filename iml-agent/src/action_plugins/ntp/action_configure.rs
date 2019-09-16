// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::agent_error::ImlAgentError;
use futures::{future, Future, Stream};
use std::path::Path;

static NTP_CONFIG_FILE: &'static str = "/etc/ntp.conf";
static MARKER: &'static str = "# IML_EDIT";
static REMOVE_MARKER: &'static str = "#REMOVE_MARKER#";
static PREFIX: &'static str = "server";

/// Gets a stream to the ntp config
fn get_ntp_config_stream() -> impl Stream<Item = String, Error = ImlAgentError> {
    iml_fs::stream_file_lines(Path::new(NTP_CONFIG_FILE)).from_err()
}

/// Writes the new config data to the config file
pub fn update_and_write_new_config(
    server: Option<String>,
) -> impl Future<Item = (), Error = ImlAgentError> {
    let s = get_ntp_config_stream();
    configure_ntp(server, s)
        .and_then(|updated_config| tokio::fs::write(NTP_CONFIG_FILE, updated_config).from_err())
        .map(drop)
}

fn configure_ntp(
    server: Option<String>,
    s: impl Stream<Item = String, Error = ImlAgentError>,
) -> impl Future<Item = String, Error = ImlAgentError> {
    s.map(reset_config)
        .filter(filter_out_remove_markers)
        .fold(
            ("".to_string(), false),
            move |(mut acc, prefix_found), line| {
                let (x, prefix_found) = if let Some(server_name) = &server {
                    transform_config(server_name.into(), line, prefix_found)
                } else {
                    (line, prefix_found)
                };

                acc.push_str(&format!("{}\n", x));
                future::ok::<_, ImlAgentError>((acc, prefix_found))
            },
        )
        .map(|(x, _)| x)
        .from_err()
}

fn transform_config(server: String, line: String, prefix_found: bool) -> (String, bool) {
    let m = line.split(" ").take(1).collect::<Vec<&str>>();
    match (m.as_slice(), prefix_found) {
        (&["server"], false) => {
            if server == "localhost" {
                (
                    format!(
                        "{}\n{}",
                        format!("server  127.127.1.0 {}", MARKER),
                        format!("fudge   127.127.1.0 stratum 10 {} {}", MARKER, line),
                    ),
                    true,
                )
            } else {
                ([PREFIX, &server, "iburst", MARKER, &line].join(" "), true)
            }
        }
        (["server"], true) => ([MARKER, &line].join(" ").to_string(), true),
        _ => (line, prefix_found),
    }
}

fn reset_config(line: String) -> String {
    if let Some(marker_location) = line.find(MARKER) {
        let end_location = marker_location + MARKER.len();
        let original = line[end_location..].trim();
        if original.len() > 0 {
            original.into()
        } else {
            REMOVE_MARKER.into()
        }
    } else {
        line
    }
}

fn filter_out_remove_markers(line: &String) -> bool {
    line.find(REMOVE_MARKER).is_none()
}

#[cfg(test)]
mod test {
    use super::*;
    use futures::Stream;
    use insta::assert_debug_snapshot;

    static ORIGINAL_CONFIG: &'static str =
        r#"# For more information about this file, see the man pages
# ntp.conf(5), ntp_acc(5), ntp_auth(5), ntp_clock(5), ntp_misc(5), ntp_mon(5).

driftfile /var/lib/ntp/drift

# Permit time synchronization with our time source, but do not
# permit the source to query or modify the service on this system.
restrict default nomodify notrap nopeer noquery

# Permit all access over the loopback interface.  This could
# be tightened as well, but to do so would effect some of
# the administrative functions.
restrict 127.0.0.1 
restrict ::1

# Hosts on local network are less restricted.
#restrict 192.168.1.0 mask 255.255.255.0 nomodify notrap

# Use public servers from the pool.ntp.org project.
# Please consider joining the pool (http://www.pool.ntp.org/join.html).
server 0.centos.pool.ntp.org iburst
server 1.centos.pool.ntp.org iburst
server 2.centos.pool.ntp.org iburst
server 3.centos.pool.ntp.org iburst

#broadcast 192.168.1.255 autokey     # broadcast server
#broadcastclient                     # broadcast client
#broadcast 224.0.1.1 autokey         # multicast server
#multicastclient 224.0.1.1           # multicast client
#manycastserver 239.255.254.254      # manycast server
#manycastclient 239.255.254.254 autokey # manycast client

# Enable public key cryptography.
#crypto

includefile /etc/ntp/crypto/pw

# Key file containing the keys and key identifiers used when operating
# with symmetric key cryptography. 
keys /etc/ntp/keys

# Specify the key identifiers which are trusted.
#trustedkey 4 8 42

# Specify the key identifier to use with the ntpdc utility.
#requestkey 8

# Specify the key identifier to use with the ntpq utility.
#controlkey 8

# Enable writing of statistics records.
#statistics clockstats cryptostats loopstats peerstats

# Disable the monitoring facility to prevent amplification attacks using ntpdc
# monlist command when default restrict does not include the noquery flag. See
# CVE-2013-5211 for more details.
# Note: Monitoring will not be disabled with the limited restriction flag.
disable monitor
"#;

    static LOCAL_HOST_CONFIG: &'static str =
        r#"# For more information about this file, see the man pages
# ntp.conf(5), ntp_acc(5), ntp_auth(5), ntp_clock(5), ntp_misc(5), ntp_mon(5).

driftfile /var/lib/ntp/drift

# Permit time synchronization with our time source, but do not
# permit the source to query or modify the service on this system.
restrict default nomodify notrap nopeer noquery

# Permit all access over the loopback interface.  This could
# be tightened as well, but to do so would effect some of
# the administrative functions.
restrict 127.0.0.1 
restrict ::1

# Hosts on local network are less restricted.
#restrict 192.168.1.0 mask 255.255.255.0 nomodify notrap

# Use public servers from the pool.ntp.org project.
# Please consider joining the pool (http://www.pool.ntp.org/join.html).
server  127.127.1.0 # IML_EDIT
fudge   127.127.1.0 stratum 10 # IML_EDIT server 0.centos.pool.ntp.org iburst
# IML_EDIT server 1.centos.pool.ntp.org iburst
# IML_EDIT server 2.centos.pool.ntp.org iburst
# IML_EDIT server 3.centos.pool.ntp.org iburst

#broadcast 192.168.1.255 autokey     # broadcast server
#broadcastclient                     # broadcast client
#broadcast 224.0.1.1 autokey         # multicast server
#multicastclient 224.0.1.1           # multicast client
#manycastserver 239.255.254.254      # manycast server
#manycastclient 239.255.254.254 autokey # manycast client

# Enable public key cryptography.
#crypto

includefile /etc/ntp/crypto/pw

# Key file containing the keys and key identifiers used when operating
# with symmetric key cryptography. 
keys /etc/ntp/keys

# Specify the key identifiers which are trusted.
#trustedkey 4 8 42

# Specify the key identifier to use with the ntpdc utility.
#requestkey 8

# Specify the key identifier to use with the ntpq utility.
#controlkey 8

# Enable writing of statistics records.
#statistics clockstats cryptostats loopstats peerstats

# Disable the monitoring facility to prevent amplification attacks using ntpdc
# monlist command when default restrict does not include the noquery flag. See
# CVE-2013-5211 for more details.
# Note: Monitoring will not be disabled with the limited restriction flag.
disable monitor
"#;

    static SERVER_CONFIG: &'static str =
        r#"# For more information about this file, see the man pages
# ntp.conf(5), ntp_acc(5), ntp_auth(5), ntp_clock(5), ntp_misc(5), ntp_mon(5).

driftfile /var/lib/ntp/drift

# Permit time synchronization with our time source, but do not
# permit the source to query or modify the service on this system.
restrict default nomodify notrap nopeer noquery

# Permit all access over the loopback interface.  This could
# be tightened as well, but to do so would effect some of
# the administrative functions.
restrict 127.0.0.1 
restrict ::1

# Hosts on local network are less restricted.
#restrict 192.168.1.0 mask 255.255.255.0 nomodify notrap

# Use public servers from the pool.ntp.org project.
# Please consider joining the pool (http://www.pool.ntp.org/join.html).
server adm.local iburst # IML_EDIT server 0.centos.pool.ntp.org iburst
# IML_EDIT server 1.centos.pool.ntp.org iburst
# IML_EDIT server 2.centos.pool.ntp.org iburst
# IML_EDIT server 3.centos.pool.ntp.org iburst

#broadcast 192.168.1.255 autokey     # broadcast server
#broadcastclient                     # broadcast client
#broadcast 224.0.1.1 autokey         # multicast server
#multicastclient 224.0.1.1           # multicast client
#manycastserver 239.255.254.254      # manycast server
#manycastclient 239.255.254.254 autokey # manycast client

# Enable public key cryptography.
#crypto

includefile /etc/ntp/crypto/pw

# Key file containing the keys and key identifiers used when operating
# with symmetric key cryptography. 
keys /etc/ntp/keys

# Specify the key identifiers which are trusted.
#trustedkey 4 8 42

# Specify the key identifier to use with the ntpdc utility.
#requestkey 8

# Specify the key identifier to use with the ntpq utility.
#controlkey 8

# Enable writing of statistics records.
#statistics clockstats cryptostats loopstats peerstats

# Disable the monitoring facility to prevent amplification attacks using ntpdc
# monlist command when default restrict does not include the noquery flag. See
# CVE-2013-5211 for more details.
# Note: Monitoring will not be disabled with the limited restriction flag.
disable monitor
"#;

    fn get_config_stream(
        config: &'static str,
    ) -> impl Stream<Item = String, Error = ImlAgentError> {
        futures::stream::iter_ok(config.lines().map(|l| l.to_string()))
    }

    #[test]
    fn test_configure_ntp_with_server_as_localhost() {
        let s = get_config_stream(ORIGINAL_CONFIG);

        let result = configure_ntp(Some("localhost".into()), s).wait().unwrap();

        assert_debug_snapshot!(result);
    }

    #[test]
    fn test_configure_ntp_with_server_as_adm() {
        let s = get_config_stream(ORIGINAL_CONFIG);
        let result = configure_ntp(Some("adm.local".into()), s).wait().unwrap();

        assert_debug_snapshot!(result);
    }

    #[test]
    fn test_configure_ntp_with_no_server_specified() {
        let s = get_config_stream(ORIGINAL_CONFIG);
        let result = configure_ntp(None, s).wait().unwrap();

        assert_debug_snapshot!(result);
    }

    #[test]
    fn test_configure_ntp_with_modified_config() {
        let s = get_config_stream(SERVER_CONFIG);
        let result = configure_ntp(Some("localhost".into()), s).wait().unwrap();

        assert_debug_snapshot!(result);
    }

    #[test]
    fn test_reset_config_with_server_markers() {
        let s = get_config_stream(SERVER_CONFIG);
        let result = s
            .map(reset_config)
            .filter(filter_out_remove_markers)
            .collect()
            .wait()
            .unwrap()
            .join("\n");

        assert_debug_snapshot!(result);
    }

    #[test]
    fn test_reset_config_with_local_server_markers() {
        let s = get_config_stream(LOCAL_HOST_CONFIG);
        let result = s
            .map(|l| l.to_string())
            .map(reset_config)
            .filter(filter_out_remove_markers)
            .collect()
            .wait()
            .unwrap()
            .join("\n");

        assert_debug_snapshot!(result);
    }

    #[test]
    fn test_reset_config_with_no_server_markers() {
        let s = get_config_stream(ORIGINAL_CONFIG);
        let result = s
            .map(|l| l.to_string())
            .map(reset_config)
            .filter(filter_out_remove_markers)
            .collect()
            .wait()
            .unwrap()
            .join("\n");

        assert_debug_snapshot!(result);
    }
}
