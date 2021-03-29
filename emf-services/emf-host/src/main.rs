// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use chrono::{DateTime, Utc};
use emf_manager_env::get_pool_limit;
use emf_postgres::get_db_pool;
use emf_service_queue::spawn_service_consumer;
use emf_wire_types::MachineId;
use futures::StreamExt;

// Default pool limit if not overridden by POOL_LIMIT
const DEFAULT_POOL_LIMIT: u32 = 4;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    emf_tracing::init();

    let pool = get_db_pool(
        get_pool_limit().unwrap_or(DEFAULT_POOL_LIMIT),
        emf_manager_env::get_port("HOST_SERVICE_PG_PORT"),
    )
    .await?;

    sqlx::migrate!("../../migrations").run(&pool).await?;

    let mut rx = spawn_service_consumer::<(MachineId, DateTime<Utc>)>(emf_manager_env::get_port(
        "HOST_SERVICE_PORT",
    ));

    while let Some((fqdn, (machine_id, boot_time))) = rx.next().await {
        sqlx::query!(
            r#"
                INSERT INTO host (machine_id, fqdn, boot_time, state)
                VALUES ($1, $2, $3, 'up')
                ON CONFLICT (machine_id) DO UPDATE
                SET
                    fqdn = excluded.fqdn,
                    boot_time = excluded.boot_time,
                    state = excluded.state
            "#,
            &machine_id.0,
            &fqdn.0,
            boot_time
        )
        .execute(&pool)
        .await?;
    }

    Ok(())
}
