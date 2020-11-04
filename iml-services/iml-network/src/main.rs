// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::TryStreamExt;
use iml_influx::{Client, Error as InfluxError, Point, Points, Precision, Value};
use iml_manager_env::{get_influxdb_addr, get_influxdb_metrics_db, get_pool_limit};
use iml_postgres::{get_db_pool, host_id_by_fqdn, sqlx, PgPool};
use iml_service_queue::service_queue::consume_data;
use iml_wire_types::{LNet, NetworkData, NetworkInterface};
use url::Url;

// Default pool limit if not overridden by POOL_LIMIT
const DEFAULT_POOL_LIMIT: u32 = 2;

async fn update_interfaces(
    pool: &PgPool,
    host_id: i32,
    interfaces: &[NetworkInterface],
) -> Result<(), sqlx::Error> {
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

    let points = Points::create_new(points);

    tracing::debug!("Writing net stats to influx.");

    influx_client
        .write_points(points, Some(Precision::Nanoseconds), None)
        .await?;

    Ok(())
}

fn parse_lnet_data(
    lnet_data: &LNet,
    host_id: i32,
) -> (Vec<String>, Vec<i32>, Vec<String>, Vec<String>, Vec<String>) {
    lnet_data
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
                        x.interfaces
                            .map(|x| x.values().into_iter().cloned().collect::<Vec<String>>()),
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
        )
}

async fn update_lnet_data(
    pool: &PgPool,
    host_id: i32,
    lnet_data: &LNet,
) -> Result<(), sqlx::Error> {
    let xs = parse_lnet_data(lnet_data, host_id);

    let x = sqlx::query!(
        r#"
            INSERT INTO nid
            (net_type, host_id, nid, status, interfaces)
            SELECT net_type, host_id, nid, status, string_to_array(interfaces, ',')::text[]
            FROM UNNEST($1::text[], $2::int[], $3::text[], $4::text[], $5::text[])
            AS t(net_type, host_id, nid, status, interfaces)
            ON CONFLICT (nid)
                DO
                UPDATE SET  host_id       = EXCLUDED.host_id,
                            net_type      = EXCLUDED.net_type,
                            status        = EXCLUDED.status,
                            interfaces    = EXCLUDED.interfaces
            RETURNING id"#,
        &xs.0,
        &xs.1,
        &xs.2,
        &xs.3,
        &xs.4,
    )
    .fetch_all(pool)
    .await?;

    tracing::error!("ids: {:?}", x);

    Ok(())
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

        let host_id = if let Some(host_id) = host_id {
            host_id
        } else {
            continue;
        };

        update_interfaces(&pool, host_id, &network_interfaces).await?;
        update_network_stats(&influx_client, host_id, &network_interfaces).await?;
        update_lnet_data(&pool, host_id, &lnet_data).await?;
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use iml_wire_types::{Net, Nid};
    use std::collections::BTreeMap;

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
                    }],
                },
                Net {
                    net_type: "tcp".into(),
                    local_nis: vec![Nid {
                        nid: "10.73.20.21@tcp".into(),
                        status: "up".into(),
                        interfaces: Some(
                            vec![(0, "eth1".into()), (1, "eth2".into())]
                                .into_iter()
                                .collect::<BTreeMap<i32, String>>(),
                        ),
                    }],
                },
                Net {
                    net_type: "o2ib".into(),
                    local_nis: vec![
                        Nid {
                            nid: "172.16.0.24@o2ib".into(),
                            status: "down".into(),
                            interfaces: Some(
                                vec![(0, "ib0".into()), (1, "ib3".into())]
                                    .into_iter()
                                    .collect::<BTreeMap<i32, String>>(),
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
                                vec![(0, "ib1".into()), (1, "ib4".into()), (2, "ib5".into())]
                                    .into_iter()
                                    .collect::<BTreeMap<i32, String>>(),
                            ),
                        }
                    ],
                },
            ],
        };

        let parsed_data = parse_lnet_data(&data, 2);

        insta::assert_debug_snapshot!(parsed_data)
    }
}
