// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::TryStreamExt;
use iml_influx::{Client, Error as InfluxError, Point, Points, Precision, Value};
use iml_manager_env::{get_influxdb_addr, get_influxdb_metrics_db, get_pool_limit};
use iml_postgres::{get_db_pool, host_id_by_fqdn, sqlx, PgPool};
use iml_service_queue::service_queue::consume_data;
use iml_wire_types::{LNet, LNetState, LndType, Net, NetworkData, NetworkInterface, Nid};
use ipnetwork::{Ipv4Network, Ipv6Network};
use std::collections::{BTreeSet, HashMap};
use url::Url;

// Default pool limit if not overridden by POOL_LIMIT
const DEFAULT_POOL_LIMIT: u32 = 2;

async fn update_interfaces(
    pool: &PgPool,
    host_id: i32,
    interfaces: &[NetworkInterface],
) -> Result<(), sqlx::Error> {
    tracing::debug!("Update interfaces.");
    let xs =
        interfaces
            .iter()
            .cloned()
            .filter_map(|x| {
                if let Some(mac_address) = x.mac_address {
                    Some((
                        mac_address,
                        x.interface,
                        x.inet4_address
                            .into_iter()
                            .map(|x| x.to_string())
                            .collect::<Vec<String>>()
                            .join(","),
                        x.inet6_address
                            .into_iter()
                            .map(|x| x.to_string())
                            .collect::<Vec<String>>()
                            .join(","),
                        x.interface_type.map(|x| x.to_string()),
                        x.is_up,
                    ))
                } else {
                    None
                }
            })
            .fold(
                (vec![], vec![], vec![], vec![], vec![], vec![], vec![]),
                |mut acc,
                 (
                    mac_address,
                    interface,
                    inet4_addresses,
                    inet6_addresses,
                    interface_type,
                    is_up,
                )| {
                    acc.0.push(mac_address);
                    acc.1.push(interface);
                    acc.2.push(inet4_addresses);
                    acc.3.push(inet6_addresses);
                    acc.4.push(interface_type);
                    acc.5.push(is_up);
                    acc.6.push(host_id);

                    acc
                },
            );

    tracing::debug!("Updating network interfaces with: {:?}", xs);

    sqlx::query!(
        r#"
            INSERT INTO network_interface 
            (mac_address, name, inet4_address, inet6_address, lnd_type, state_up, host_id)
            SELECT mac_address, name, string_to_array(inet4_address, ',')::inet[], string_to_array(inet6_address, ',')::inet[], lnd_type, state_up, host_id
            FROM UNNEST($1::text[], $2::text[], $3::text[], $4::text[], $5::lnd_network_type[], $6::bool[], $7::int[])
            AS t(mac_address, name, inet4_address, inet6_address, lnd_type, state_up, host_id)
            ON CONFLICT (mac_address)
                DO
                UPDATE SET  name          = EXCLUDED.name,
                            inet4_address = EXCLUDED.inet4_address,
                            inet6_address = EXCLUDED.inet6_address,
                            lnd_type      = EXCLUDED.lnd_type,
                            state_up      = EXCLUDED.state_up,
                            host_id       = EXCLUDED.host_id"#,
            &xs.0,
            &xs.1,
            &xs.2,
            &xs.3,
            &xs.4 as &[Option<String>],
            &xs.5,
            &xs.6,
    )
    .execute(pool)
    .await?;

    Ok(())
}

async fn handle_interfaces(
    pool: &PgPool,
    host_id: i32,
    interfaces: &[NetworkInterface],
    interface_cache: &mut HashMap<i32, Vec<NetworkInterface>>,
) -> Result<(), sqlx::Error> {
    if let Some(cached_interfaces) = interface_cache.get(&host_id) {
        if cached_interfaces.as_slice() != interfaces {
            tracing::debug!("Cache and interfaces are different. Updating cache and database.");
            interface_cache.insert(host_id, interfaces.to_vec());
            update_interfaces(pool, host_id, interfaces).await?;
        } else {
            tracing::debug!("Cache and interfaces for this host are identical. Nothing to update.")
        }
    } else {
        interface_cache.insert(host_id, interfaces.to_vec());
        update_interfaces(pool, host_id, interfaces).await?;
    }

    Ok(())
}

async fn update_network_stats(
    influx_client: &Client,
    host_id: i32,
    interfaces: &[NetworkInterface],
) -> Result<(), InfluxError> {
    let points = interfaces
        .iter()
        .cloned()
        .filter_map(|x: NetworkInterface| {
            x.stats
                .clone()
                .map(|stat| (x.interface, stat.rx.bytes, stat.tx.bytes))
        })
        .map(|(interface, rx_bytes, tx_bytes)| {
            Point::new("net")
                .add_tag("interface", Value::String(interface))
                .add_tag("host_id", Value::Integer(host_id as i64))
                .add_field("rx_bytes", Value::Integer(rx_bytes as i64))
                .add_field("tx_bytes", Value::Integer(tx_bytes as i64))
        })
        .collect::<Vec<Point>>();

    if points.len() > 0 {
        let points = Points::create_new(points);

        tracing::debug!("Writing net stats to influx.");

        influx_client
            .write_points(points, Some(Precision::Nanoseconds), None)
            .await?;
    }

    Ok(())
}

fn parse_lnet_data(
    lnet_data: &LNet,
    host_id: i32,
) -> (
    Option<(Vec<String>, Vec<i32>, Vec<String>, Vec<String>, Vec<String>)>,
    LNetState,
) {
    if lnet_data.net.len() == 0 {
        return (None, lnet_data.state.clone());
    }

    let xs = lnet_data
        .net
        .iter()
        .cloned()
        .filter(|x| x.net_type != "lo")
        .flat_map(|lnet| {
            let net_type = lnet.net_type.to_string();

            lnet.local_nis
                .into_iter()
                .map(|x| {
                    (
                        net_type.to_string(),
                        x.nid,
                        x.status,
                        x.interfaces.map(|x| x.into_iter().collect::<Vec<String>>()),
                    )
                })
                .collect::<Vec<(String, String, String, Option<Vec<String>>)>>()
        })
        .fold(
            (vec![], vec![], vec![], vec![], vec![]),
            |mut acc, (net_type, nid, status, interfaces)| {
                acc.0.push(net_type);
                acc.1.push(host_id);
                acc.2.push(nid);
                acc.3.push(status);
                acc.4.push(
                    interfaces
                        .map(|x| x.join(","))
                        .unwrap_or_else(|| "".to_string()),
                );

                acc
            },
        );

    if xs.0.len() > 0 {
        (Some(xs), lnet_data.state.clone())
    } else {
        (None, lnet_data.state.clone())
    }
}

async fn handle_lnet_data(
    pool: &PgPool,
    host_id: i32,
    lnet_data: &LNet,
    lnet_cache: &mut HashMap<i32, LNet>,
) -> Result<(), sqlx::Error> {
    if let Some(cached_lnet) = lnet_cache.get(&host_id) {
        if cached_lnet != lnet_data {
            tracing::debug!("Cache and lnet data are different. Updating cache and database.");
            lnet_cache.insert(host_id, lnet_data.clone());
            update_lnet_data(pool, host_id, lnet_data).await?;
        } else {
            tracing::debug!("Cache and lnet data for this host are identical. Nothing to update.")
        }
    } else {
        lnet_cache.insert(host_id, lnet_data.clone());
        update_lnet_data(pool, host_id, lnet_data).await?;
    }

    Ok(())
}

async fn update_lnet_data(
    pool: &PgPool,
    host_id: i32,
    lnet_data: &LNet,
) -> Result<(), sqlx::Error> {
    tracing::debug!("Updating lnet data: {:?} on host: {}", lnet_data, host_id);
    let lnet_data = parse_lnet_data(lnet_data, host_id);

    if let Some(xs) = lnet_data.0 {
        tracing::debug!("updating lnet with: {:?} and state {}", xs, lnet_data.1);
        sqlx::query!(
            r#"
                WITH updated AS (
                    INSERT INTO nid
                    (net_type, host_id, nid, status, interfaces)
                    SELECT net_type, host_id, nid, status, string_to_array(interfaces, ',')::text[]
                    FROM UNNEST($1::text[], $2::int[], $3::text[], $4::text[], $5::text[])
                    AS t(net_type, host_id, nid, status, interfaces)
                    ON CONFLICT (host_id, nid)
                        DO
                        UPDATE SET  net_type      = EXCLUDED.net_type,
                                    status        = EXCLUDED.status,
                                    interfaces    = EXCLUDED.interfaces,
                                    id            = nid.id
                    RETURNING id
                )

                INSERT INTO lnet
                (host_id, state, nids)
                (SELECT $6, $7::lnet_state, array_agg(id) from updated)
                ON CONFLICT (host_id)
                    DO
                    UPDATE SET nids  = EXCLUDED.nids,
                            state = EXCLUDED.state,
                            id = lnet.id;
                    "#,
            &xs.0,
            &xs.1,
            &xs.2,
            &xs.3,
            &xs.4,
            &host_id,
            lnet_data.1.to_string() as String,
        )
        .execute(pool)
        .await?;

        // Delete any nids on the matching host that are currently assigned on the nid table but are no longer
        // being reported by the storage server.
        sqlx::query!(
            r#"
            DELETE FROM nid WHERE host_id=$1 AND NOT (nid = ANY($2::text[]))
        "#,
            &host_id,
            &xs.2,
        )
        .execute(pool)
        .await?;
    } else {
        tracing::debug!(
            "LNet data is empty and thus may be unloaded on {}.",
            &host_id
        );

        // If there is no LNet data then set the state and clear out the nids array.
        sqlx::query!(
            r#"UPDATE lnet SET state=$1::lnet_state, nids=array[]::int[] WHERE host_id=$2"#,
            lnet_data.1.to_string() as String,
            &host_id,
        )
        .execute(pool)
        .await?;

        // If there is no data then remove all the nids for this host on the nid table.
        sqlx::query!(
            r#"
            DELETE FROM nid WHERE host_id=$1;
        "#,
            &host_id,
        )
        .execute(pool)
        .await?;
    }

    Ok(())
}

async fn get_interface_cache(
    pool: &PgPool,
) -> Result<HashMap<i32, Vec<NetworkInterface>>, sqlx::Error> {
    let xs = sqlx::query!(
        r#"SELECT mac_address, 
            name, 
            inet4_address, 
            inet6_address, 
            lnd_type as "lnd_type: LndType", 
            state_up, 
            host_id  
        FROM network_interface"#
    )
    .fetch_all(pool)
    .await?
    .into_iter()
    .map(|x| {
        (
            x.host_id,
            NetworkInterface {
                interface: x.name,
                mac_address: Some(x.mac_address),
                interface_type: x.lnd_type,
                inet4_address: x
                    .inet4_address
                    .into_iter()
                    .map(|x| {
                        let net = x.to_string();
                        let net: Ipv4Network = net.parse().expect("ipv4 address");

                        net
                    })
                    .collect(),
                inet6_address: x
                    .inet6_address
                    .into_iter()
                    .map(|x| {
                        let net = x.to_string();
                        let net: Ipv6Network = net.parse().expect("ipv6 address");

                        net
                    })
                    .collect(),
                stats: None,
                is_up: x.state_up,
                is_slave: false,
            },
        )
    })
    .fold(
        HashMap::<i32, Vec<NetworkInterface>>::new(),
        |mut acc, (host_id, interface)| {
            let interfaces = acc.entry(host_id).or_insert_with(|| vec![]);
            interfaces.push(interface);

            acc
        },
    );

    Ok(xs)
}

async fn get_lnet_cache(pool: &PgPool) -> Result<HashMap<i32, LNet>, sqlx::Error> {
    let xs: HashMap<i32, LNet> = sqlx::query!(r#"
        SELECT l.host_id, l.state as "state: LNetState", n.net_type, n.nid, n.status, n.interfaces FROM lnet AS l
        INNER JOIN nid AS n ON n.id = ANY(l.nids)"#,
    )
    .fetch_all(pool)
    .await?
    .into_iter()
    .fold(HashMap::<i32, LNet>::new(), |mut acc, x| {
        let lnet = acc.entry(x.host_id).or_insert_with(|| LNet::default());

        let net_type = x.net_type.to_string();
        let net_type2 = x.net_type.to_string();

        if lnet.net
            .iter()
            .find(|x| x.net_type == net_type)
            .is_some() {
            let net = lnet.net
                .iter()
                .cloned()
                .map(|mut net| {
                    if net.net_type.to_string() == net_type {
                        net.local_nis.insert(Nid {
                            nid: x.nid.to_string(),
                            status: x.status.to_string(),
                            interfaces: Some(x.interfaces.iter().cloned().collect::<BTreeSet<String>>())
                        });
                    }

                    net
                })
                .collect::<BTreeSet<Net>>();

            lnet.net = net;
        } else {
            let nid = Nid {
                nid: x.nid,
                status: x.status,
                interfaces: Some(x.interfaces.into_iter().collect::<BTreeSet<String>>()),
            };

            let net = Net {
                net_type: net_type2,
                local_nis: vec![nid].iter().cloned().collect::<BTreeSet<Nid>>(),
            };

            lnet.net = vec![net].into_iter().collect::<BTreeSet<Net>>();
        }

        lnet.state = x.state;

        acc
    });

    Ok(xs)
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    iml_tracing::init();

    let pool = get_db_pool(get_pool_limit().unwrap_or(DEFAULT_POOL_LIMIT)).await?;

    let rabbit_pool = iml_rabbit::connect_to_rabbit(1);

    let conn = iml_rabbit::get_conn(rabbit_pool).await?;

    let ch = iml_rabbit::create_channel(&conn).await?;

    let mut s = consume_data::<NetworkData>(&ch, "rust_agent_network_rx");

    sqlx::migrate!("../../migrations").run(&pool).await?;

    let influx_url: String = format!("http://{}", get_influxdb_addr());
    let influx_client = Client::new(
        Url::parse(&influx_url).expect("Influx URL is invalid."),
        get_influxdb_metrics_db(),
    );

    let mut interface_cache: HashMap<i32, Vec<NetworkInterface>> =
        get_interface_cache(&pool).await?;
    tracing::debug!("interface cache: {:?}", interface_cache);
    let mut lnet_cache: HashMap<i32, LNet> = get_lnet_cache(&pool).await?;
    tracing::debug!("lnet cache: {:?}", lnet_cache);

    while let Some((
        fqdn,
        NetworkData {
            network_interfaces,
            lnet_data,
        },
    )) = s.try_next().await?
    {
        tracing::debug!(
            "fqdn: {:?} interfaces: {:?}, lnet_data: {:?}",
            fqdn,
            network_interfaces,
            lnet_data
        );

        let host_id = host_id_by_fqdn(&fqdn, &pool).await?;
        tracing::debug!("Updating network data for host {:?}", host_id);

        let host_id = if let Some(host_id) = host_id {
            host_id
        } else {
            continue;
        };

        handle_interfaces(&pool, host_id, &network_interfaces, &mut interface_cache).await?;
        update_network_stats(&influx_client, host_id, &network_interfaces).await?;
        handle_lnet_data(&pool, host_id, &lnet_data, &mut lnet_cache).await?;
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use iml_wire_types::{LNetState, Net, Nid};

    #[test]
    fn test_parse_lnetctl_data() {
        let data = LNet {
            net: vec![
                Net {
                    net_type: "lo".into(),
                    local_nis: vec![Nid {
                        nid: "0@lo".into(),
                        status: "up".into(),
                        interfaces: None,
                    }]
                    .iter()
                    .cloned()
                    .collect::<BTreeSet<Nid>>(),
                },
                Net {
                    net_type: "tcp".into(),
                    local_nis: vec![Nid {
                        nid: "10.73.20.21@tcp".into(),
                        status: "up".into(),
                        interfaces: Some(
                            vec!["eth1".into(), "eth2".into()]
                                .into_iter()
                                .collect::<BTreeSet<String>>(),
                        ),
                    }]
                    .iter()
                    .cloned()
                    .collect::<BTreeSet<Nid>>(),
                },
                Net {
                    net_type: "o2ib".into(),
                    local_nis: vec![
                        Nid {
                            nid: "172.16.0.24@o2ib".into(),
                            status: "down".into(),
                            interfaces: Some(
                                vec!["ib0".into(), "ib3".into()]
                                    .into_iter()
                                    .collect::<BTreeSet<String>>(),
                            ),
                        },
                        Nid {
                            nid: "172.16.0.26@o2ib".into(),
                            status: "up".into(),
                            interfaces: None,
                        },
                        Nid {
                            nid: "172.16.0.28@o2ib".into(),
                            status: "up".into(),
                            interfaces: Some(
                                vec!["ib1".into(), "ib4".into(), "ib5".into()]
                                    .into_iter()
                                    .collect::<BTreeSet<String>>(),
                            ),
                        },
                    ]
                    .into_iter()
                    .collect::<BTreeSet<Nid>>(),
                },
            ]
            .into_iter()
            .collect::<BTreeSet<Net>>(),
            state: LNetState::Up,
        };

        let parsed_data = parse_lnet_data(&data, 2);

        insta::with_settings!({sort_maps => true}, {
            insta::assert_debug_snapshot!(parsed_data)
        });
    }

    #[test]
    fn test_parse_empty_lnetctl_data() {
        let data = LNet {
            net: vec![].into_iter().collect::<BTreeSet<Net>>(),
            state: LNetState::Unloaded,
        };

        let parsed_data = parse_lnet_data(&data, 2);

        insta::assert_debug_snapshot!(parsed_data)
    }
}
