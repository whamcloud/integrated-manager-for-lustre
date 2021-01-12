// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::action_plugins::ntp::common::{get_ntp_config_stream, MARKER};
use crate::agent_error::EmfAgentError;
use futures::{future, stream::Stream, Future, TryFutureExt, TryStreamExt};

fn has_marker(
    s: impl Stream<Item = Result<String, EmfAgentError>>,
) -> impl Future<Output = Result<bool, EmfAgentError>> {
    s.try_fold(false, |acc, x: String| {
        future::ok::<_, EmfAgentError>(acc || x.find(MARKER).is_some())
    })
    .err_into()
}

pub fn is_ntp_configured(_: ()) -> impl Future<Output = Result<bool, EmfAgentError>> {
    let s = get_ntp_config_stream();
    has_marker(s)
}

#[cfg(test)]
mod test {
    use super::*;
    use futures::Stream;

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

    static CONFIGURED_CONFIG: &'static str = r#"# For more information about this file, see the man pages
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
        futures::stream::iter(config.lines().map(|l| Ok(l.to_string())))
    }

    #[tokio::test]
    async fn test_config_without_marker_is_not_configured() -> Result<(), EmfAgentError> {
        let s = get_config_stream(ORIGINAL_CONFIG);
        assert_eq!(false, has_marker(s).await?);

        Ok(())
    }

    #[tokio::test]
    async fn test_config_with_marker_is_configured() -> Result<(), EmfAgentError> {
        let s = get_config_stream(CONFIGURED_CONFIG);
        assert_eq!(true, has_marker(s).await?);

        Ok(())
    }
}
