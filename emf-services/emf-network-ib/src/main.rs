// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use emf_influx::{Client, Point, Points, Precision, Value};
use emf_manager_env::{get_influxdb_metrics_db, get_pool_limit};
use emf_postgres::{get_db_pool, host_id_by_fqdn};
use emf_service_queue::spawn_service_consumer;
use emf_wire_types::IBInterface;
use futures::StreamExt;
use url::Url;

// Default pool limit if not overridden by POOL_LIMIT
const DEFAULT_POOL_LIMIT: u32 = 1;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    emf_tracing::init();

    let pg_port = emf_manager_env::get_port("NETWORK_IB_SERVICE_PG_PORT");
    let pool = get_db_pool(get_pool_limit().unwrap_or(DEFAULT_POOL_LIMIT), pg_port).await?;

    sqlx::migrate!("../../migrations").run(&pool).await?;

    let mut rx = spawn_service_consumer::<Vec<IBInterface>>(emf_manager_env::get_port(
        "NETWORK_IB_SERVICE_PORT",
    ));

    let influx_url: String = format!(
        "http://127.0.0.1:{}",
        emf_manager_env::get_port("NETWORK_IB_SERVICE_INFLUX_PORT")
    );
    let influx_client = Client::new(
        Url::parse(&influx_url).expect("Influx URL is invalid."),
        get_influxdb_metrics_db(),
    );

    while let Some((fqdn, ib_interfaces)) = rx.next().await {
        tracing::debug!("fqdn: {:?} ib_interfaces: {:?}", fqdn, ib_interfaces);

        let host_id = host_id_by_fqdn(&fqdn, &pool).await?;

        let host_id = if let Some(host_id) = host_id {
            host_id
        } else {
            continue;
        };

        let points = ib_interfaces
            .iter()
            .map(|x: &IBInterface| {
                Point::new("infiniband")
                    .add_tag("host", Value::String(fqdn.to_string()))
                    .add_tag("host_id", Value::Integer(host_id as i64))
                    .add_tag("device", Value::String(x.interface.to_string()))
                    .add_field("port_rcv_data", Value::Integer(x.rcv_byte_total as i64))
                    .add_field("port_xmit_data", Value::Integer(x.xmit_byte_total as i64))
            })
            .collect::<Vec<Point>>();

        let points = Points::create_new(points);

        tracing::debug!("Writing net stats to influx.");

        influx_client
            .write_points(points, Some(Precision::Seconds), None)
            .await?;
    }

    Ok(())
}
