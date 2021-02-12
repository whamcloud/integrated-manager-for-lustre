// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use emf_change::{Changeable, Changes, Deletions, GetChanges as _, Upserts};
use emf_postgres::get_db_pool;
use emf_request_retry::{retry_future, RetryAction};
use emf_sfa::{db, EmfSfaError, SfaClassExt as _};
use emf_tracing::tracing;
use futures::{future, Future};
use sqlx::postgres::PgPool;
use std::{fmt::Debug, time::Duration};
use tokio::time;
use url::Url;

fn retry_fn<F, T, E>(endpoints: &[Url], f: impl Fn(u32) -> F) -> impl Future<Output = Result<T, E>>
where
    F: Future<Output = Result<T, E>>,
    E: Debug,
{
    let len = (endpoints.len() - 1) as u32;

    let policy = move |k: u32, e| {
        if k < len {
            RetryAction::RetryNow
        } else {
            RetryAction::ReturnError(e)
        }
    };

    retry_future(f, policy)
}

#[tokio::main]
async fn main() -> Result<(), EmfSfaError> {
    emf_tracing::init();

    let endpoints = emf_manager_env::get_sfa_endpoints();

    let endpoints = match endpoints {
        Some(x) => x,
        None => {
            tracing::info!("No endpoints found, exiting.");

            return Ok(());
        }
    };

    let client = wbem_client::get_client(true)?;

    let pool = get_db_pool(2, emf_manager_env::get_port("SFA_PG_PORT")).await?;

    let mut interval = time::interval(Duration::from_secs(5));

    let mut old_drives = db::disk_drive::all(&pool).await?;

    let mut old_enclosures = db::enclosure::all(&pool).await?;

    let mut old_jobs = db::job::all(&pool).await?;

    let mut old_power_supplies = db::power_supply::all(&pool).await?;

    let mut old_controllers = db::controller::all(&pool).await?;

    loop {
        interval.tick().await;

        let endpoints = &endpoints[0];

        let fut1 = retry_fn(endpoints, |c| {
            client.fetch_sfa_enclosures(endpoints[c as usize].clone())
        });

        let fut2 = retry_fn(endpoints, |c| {
            client.fetch_sfa_storage_system(endpoints[c as usize].clone())
        });

        let fut3 = retry_fn(endpoints, |c| {
            client.fetch_sfa_disk_drives(endpoints[c as usize].clone())
        });

        let fut4 = retry_fn(endpoints, |c| {
            client.fetch_sfa_jobs(endpoints[c as usize].clone())
        });

        let fut5 = retry_fn(endpoints, |c| {
            client.fetch_sfa_power_supply(endpoints[c as usize].clone())
        });

        let (new_enclosures, x, new_drives, new_jobs, new_power_supplies) =
            future::try_join5(fut1, fut2, fut3, fut4, fut5).await?;

        let new_controllers = retry_fn(endpoints, |c| {
            client.fetch_sfa_controllers(endpoints[c as usize].clone())
        })
        .await?;

        tracing::trace!("SfaStorageSystem {:?}", x);
        tracing::trace!("SfaEnclosures {:?}", new_enclosures);
        tracing::trace!("SfaDiskDrives {:?}", new_drives);
        tracing::trace!("SfaJobs {:?}", new_jobs);
        tracing::trace!("SfaPowerSupply {:?}", new_power_supplies);
        tracing::trace!("SfaController {:?}", new_controllers);

        let (enclosure_upsert, enclosure_remove) = build_changes(
            db::enclosure::batch_upsert,
            db::enclosure::batch_delete,
            new_enclosures.get_changes(&old_enclosures),
            pool.clone(),
        );

        let (drive_upsert, drive_remove) = build_changes(
            db::disk_drive::batch_upsert,
            db::disk_drive::batch_delete,
            new_drives.get_changes(&old_drives),
            pool.clone(),
        );

        let (job_upsert, job_remove) = build_changes(
            db::job::batch_upsert,
            db::job::batch_delete,
            new_jobs.get_changes(&old_jobs),
            pool.clone(),
        );

        let (power_supply_upsert, power_supply_remove) = build_changes(
            db::power_supply::batch_upsert,
            db::power_supply::batch_delete,
            new_power_supplies.get_changes(&old_power_supplies),
            pool.clone(),
        );

        let (controller_upsert, controller_remove) = build_changes(
            db::controller::batch_upsert,
            db::controller::batch_delete,
            new_controllers.get_changes(&old_controllers),
            pool.clone(),
        );

        db::storage_system::upsert(x, &pool).await?;

        enclosure_upsert.await?;

        controller_upsert.await?;

        controller_remove.await?;

        power_supply_upsert.await?;

        power_supply_remove.await?;

        drive_upsert.await?;

        job_upsert.await?;

        job_remove.await?;

        drive_remove.await?;

        enclosure_remove.await?;

        old_drives = new_drives;

        old_enclosures = new_enclosures;

        old_jobs = new_jobs;

        old_power_supplies = new_power_supplies;

        old_controllers = new_controllers;
    }
}

fn build_changes<
    'a,
    T: Changeable,
    F: Future<Output = Result<(), EmfSfaError>> + 'a,
    F2: Future<Output = Result<(), EmfSfaError>> + 'a,
>(
    upsert_fn: fn(Upserts<&'a T>, pool: PgPool) -> F,
    delete_fn: fn(Deletions<&'a T>, pool: PgPool) -> F2,
    changes: Changes<'a, T>,
    pool: PgPool,
) -> (
    impl Future<Output = Result<(), EmfSfaError>> + 'a,
    impl Future<Output = Result<(), EmfSfaError>> + 'a,
) {
    let (upserts, deletions) = changes;

    let pool2 = pool.clone();

    let a = async move {
        if let Some(x) = upserts {
            upsert_fn(x, pool).await?;
        };

        Ok(())
    };

    let b = async move {
        if let Some(x) = deletions {
            delete_fn(x, pool2).await?;
        }

        Ok(())
    };

    (a, b)
}
