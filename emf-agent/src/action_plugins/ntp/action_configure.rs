// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::action_plugins::ntp::common::{
    get_ntp_config_stream, MARKER, NTP_CONFIG_FILE, PREFIX, REMOVE_MARKER,
};
use crate::agent_error::EmfAgentError;
use futures::{future, Future, Stream, TryFutureExt, TryStreamExt};

/// Writes the new config data to the config file
pub async fn update_and_write_new_config(server: Option<String>) -> Result<(), EmfAgentError> {
    let s = get_ntp_config_stream();

    let updated_config = configure_ntp(server, s).await?;

    tokio::fs::write(NTP_CONFIG_FILE, updated_config).await?;

    Ok(())
}

fn configure_ntp(
    server: Option<String>,
    s: impl Stream<Item = Result<String, EmfAgentError>>,
) -> impl Future<Output = Result<String, EmfAgentError>> {
    s.map_ok(reset_config)
        .try_filter(|x| future::ready(filter_out_remove_markers(x)))
        .try_fold(
            ("".to_string(), false),
            move |(mut acc, prefix_found), line| {
                let (x, prefix_found) = if let Some(server_name) = &server {
                    transform_config(server_name.into(), line, prefix_found)
                } else {
                    (line, prefix_found)
                };

                acc.push_str(&x);
                acc.push('\n');

                future::ok::<_, EmfAgentError>((acc, prefix_found))
            },
        )
        .map_ok(|(x, _)| x)
        .err_into()
}

fn transform_config(server: String, line: String, prefix_found: bool) -> (String, bool) {
    let m = line.split(' ').take(1).collect::<Vec<&str>>();
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
        (["server"], true) => ([MARKER, &line].join(" "), true),
        _ => (line, prefix_found),
    }
}

fn reset_config(line: String) -> String {
    if let Some(marker_location) = line.find(MARKER) {
        let end_location = marker_location + MARKER.len();
        let original = line[end_location..].trim();
        if !original.is_empty() {
            original.into()
        } else {
            REMOVE_MARKER.into()
        }
    } else {
        line
    }
}

fn filter_out_remove_markers(line: &str) -> bool {
    line.find(REMOVE_MARKER).is_none()
}

#[cfg(test)]
mod test {
    use super::*;
    use futures::{stream, Stream};
    use insta::assert_debug_snapshot;

    static ORIGINAL_CONFIG: &'static str = r#"# For more information about this file, see the man pages
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

    static LOCAL_HOST_CONFIG: &'static str = r#"# For more information about this file, see the man pages
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
server  127.127.1.0 # EMF_EDIT
fudge   127.127.1.0 stratum 10 # EMF_EDIT server 0.centos.pool.ntp.org iburst
# EMF_EDIT server 1.centos.pool.ntp.org iburst
# EMF_EDIT server 2.centos.pool.ntp.org iburst
# EMF_EDIT server 3.centos.pool.ntp.org iburst

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

    static SERVER_CONFIG: &'static str = r#"# For more information about this file, see the man pages
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
server adm.local iburst # EMF_EDIT server 0.centos.pool.ntp.org iburst
# EMF_EDIT server 1.centos.pool.ntp.org iburst
# EMF_EDIT server 2.centos.pool.ntp.org iburst
# EMF_EDIT server 3.centos.pool.ntp.org iburst

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
    ) -> impl Stream<Item = Result<String, EmfAgentError>> {
        stream::iter(config.lines().map(|l| l.to_string()).map(Ok))
    }

    #[tokio::test]
    async fn test_configure_ntp_with_server_as_localhost() -> Result<(), EmfAgentError> {
        let s = get_config_stream(ORIGINAL_CONFIG);

        let result = configure_ntp(Some("localhost".into()), s).await?;

        assert_debug_snapshot!(result);

        Ok(())
    }

    #[tokio::test]
    async fn test_configure_ntp_with_server_as_adm() -> Result<(), EmfAgentError> {
        let s = get_config_stream(ORIGINAL_CONFIG);
        let result = configure_ntp(Some("adm.local".into()), s).await?;

        assert_debug_snapshot!(result);

        Ok(())
    }

    #[tokio::test]
    async fn test_configure_ntp_with_no_server_specified() -> Result<(), EmfAgentError> {
        let s = get_config_stream(ORIGINAL_CONFIG);
        let result = configure_ntp(None, s).await?;

        assert_debug_snapshot!(result);

        Ok(())
    }

    #[tokio::test]
    async fn test_configure_ntp_with_modified_config() -> Result<(), EmfAgentError> {
        let s = get_config_stream(SERVER_CONFIG);
        let result = configure_ntp(Some("localhost".into()), s).await?;

        assert_debug_snapshot!(result);

        Ok(())
    }

    #[tokio::test]
    async fn test_reset_config_with_server_markers() -> Result<(), EmfAgentError> {
        let s = get_config_stream(SERVER_CONFIG);
        let result = s
            .map_ok(reset_config)
            .try_filter(|x| future::ready(filter_out_remove_markers(x)))
            .try_collect::<Vec<_>>()
            .await?
            .join("\n");

        assert_debug_snapshot!(result);

        Ok(())
    }

    #[tokio::test]
    async fn test_reset_config_with_local_server_markers() -> Result<(), EmfAgentError> {
        let s = get_config_stream(LOCAL_HOST_CONFIG);
        let result = s
            .map_ok(|l| l.to_string())
            .map_ok(reset_config)
            .try_filter(|x| future::ready(filter_out_remove_markers(x)))
            .try_collect::<Vec<_>>()
            .await?
            .join("\n");

        assert_debug_snapshot!(result);

        Ok(())
    }

    #[tokio::test]
    async fn test_reset_config_with_no_server_markers() -> Result<(), EmfAgentError> {
        let s = get_config_stream(ORIGINAL_CONFIG);
        let result = s
            .map_ok(|l| l.to_string())
            .map_ok(reset_config)
            .try_filter(|x| future::ready(filter_out_remove_markers(x)))
            .try_collect::<Vec<_>>()
            .await?
            .join("\n");

        assert_debug_snapshot!(result);

        Ok(())
    }
}
