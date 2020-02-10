// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

//! # iml-devices
//!
//! This module is a host side plugin to persist devices to the db.
//!
//! It populates two tables, `device` and `device_host`.
//!
//! A `device` is a generic device that may be present on multiple hosts.
//!
//! A `device_host` is the instance of that device on a host.
//!
//! `device` to `device_host` is a 1:M relationship.
//!
//! Whenever a message is received, `Device` and `DeviceHost` records are loaded from the
//! database.
//!
//! The incoming devices are then converted to a db compatible format and a db transaction is started. Local device changes and
//! device-host changes are
//! persisted to the database.
//!
//! Finally, virtual devices are checked both on incoming and existing devices and relevant changes are made.
//!
//! The choice to persist to the database is because:
//!
//! 1. The need to have a "balanced" set of Lustre targets, and for this balance to be stable across ticks of
//!    device discovery.
//! 2. The need for devices to not be forgotten if they dissapear from a device host, but instead be raised as an alert.
//!

use futures::TryStreamExt;
use iml_devices::{db, error};
use iml_postgres::connect;
use iml_service_queue::service_queue::consume_data;
use std::collections::BTreeMap;
use tracing_subscriber::{fmt::Subscriber, EnvFilter};

#[tokio::main]
async fn main() -> Result<(), error::ImlDevicesError> {
    let subscriber = Subscriber::builder()
        .with_env_filter(EnvFilter::from_default_env())
        .finish();

    tracing::subscriber::set_global_default(subscriber).unwrap();

    let mut s = consume_data("rust_agent_device_rx");

    while let Some((fqdn, flat_devices)) = s.try_next().await? {
        let (incoming_devices, incoming_device_hosts) =
            db::convert_flat_devices(&flat_devices, fqdn.clone());

        let (mut client, conn) = connect().await?;

        tokio::spawn(async {
            conn.await
                .unwrap_or_else(|e| tracing::error!("DB connection error {}", e));
        });

        let db_devices = db::get_db_devices(&mut client).await?;

        let db_device_hosts = db::get_db_device_hosts(&mut client).await?;

        let db_device_hosts = db_device_hosts
            .into_iter()
            .fold(BTreeMap::new(), |mut acc, x| {
                acc.insert((x.device_id.clone(), x.fqdn.clone()), x);

                acc
            });

        let local_db_device_hosts = db::get_local_device_hosts(&db_device_hosts, &fqdn);
        let other_device_hosts = db::get_other_device_hosts(&db_device_hosts, &fqdn);

        let local_db_devices = db::get_local_devices(&local_db_device_hosts, &db_devices);
        let other_devices = db::get_devices_by_device_host(&other_device_hosts, &db_devices);

        let mut transaction = client.transaction().await?;

        db::persist_local_device_hosts(
            &mut transaction,
            &incoming_device_hosts,
            &local_db_device_hosts,
        )
        .await?;

        db::persist_local_devices(
            &mut transaction,
            &incoming_devices,
            &other_devices,
            &local_db_devices,
        )
        .await?;

        db::update_virtual_devices(
            &mut transaction,
            &fqdn,
            &incoming_devices,
            &incoming_device_hosts,
            &db_devices,
            &db_device_hosts,
        )
        .await?;

        transaction.commit().await?;
    }

    Ok(())
}
