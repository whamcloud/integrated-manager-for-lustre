// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use async_trait::async_trait;
use futures::{future, TryFutureExt};
use iml_orm::{
    sfa::{SfaClassError, SfaDiskDrive, SfaEnclosure, SfaStorageSystem},
    tokio_diesel::{AsyncError, AsyncRunQueryDsl as _},
    DbPool, GetChanges as _,
};
use iml_tracing::tracing;
use std::{convert::TryInto as _, time::Duration};
use thiserror::Error;
use tokio::time;
use url::Url;
use wbem_client::{resp::Instance, Client, ClientExt};

#[derive(Error, Debug)]
enum ImlSfaError {
    #[error(transparent)]
    WbemClient(#[from] wbem_client::WbemClientError),
    #[error(transparent)]
    SfaClass(#[from] SfaClassError),
    #[error(transparent)]
    Async(#[from] AsyncError),
    #[error(transparent)]
    ImlOrm(#[from] iml_orm::ImlOrmError),
}

#[tokio::main]
async fn main() -> Result<(), ImlSfaError> {
    iml_tracing::init();

    let pool = iml_orm::pool()?;

    let endpoints = iml_manager_env::get_sfa_endpoints();

    let endpoints = match endpoints {
        Some(x) => x,
        None => {
            tracing::info!("No endpoints found, exiting.");

            return Ok(());
        }
    };

    let client = wbem_client::get_client(true)?;

    let mut interval = time::interval(Duration::from_secs(5));

    let mut old_drives = SfaDiskDrive::all()
        .load_async::<SfaDiskDrive>(&pool)
        .await?;

    let mut old_enclosures = SfaEnclosure::all()
        .load_async::<SfaEnclosure>(&pool)
        .await?;

    loop {
        interval.tick().await;

        let fut1 = client.fetch_sfa_enclosures(endpoints[0][0].clone());

        let fut2 = client.fetch_sfa_storage_system(endpoints[0][0].clone());

        let fut3 = client.fetch_sfa_disk_drives(endpoints[0][0].clone());

        let (new_enclosures, x, new_drives) = future::try_join3(fut1, fut2, fut3).await?;

        tracing::debug!("SfaStorageSystem {:?}", x);
        tracing::debug!("SfaEnclosures {:?}", new_enclosures);
        tracing::debug!("SfaDiskDrives {:?}", new_drives);

        SfaStorageSystem::upsert(x).execute_async(&pool).await?;

        update_drives(&new_drives, &old_drives, &pool).await?;

        old_drives = new_drives;

        update_enclosures(&new_enclosures, &old_enclosures, &pool).await?;

        old_enclosures = new_enclosures;
    }
}

async fn update_enclosures(
    new_enclosures: &Vec<SfaEnclosure>,
    old_enclosures: &Vec<SfaEnclosure>,
    pool: &DbPool,
) -> Result<(), ImlSfaError> {
    let (add, update, remove) = new_enclosures.get_changes(&old_enclosures);

    if let Some(add) = add {
        SfaEnclosure::batch_insert(add).execute_async(pool).await?;
    }

    if let Some(update) = update {
        SfaEnclosure::batch_upsert(update)
            .execute_async(pool)
            .await?;
    }

    if let Some(remove) = remove {
        let indexes = remove.0.into_iter().map(|x| &x.index).copied().collect();

        SfaEnclosure::batch_remove(indexes)
            .execute_async(pool)
            .await?;
    }

    Ok(())
}

async fn update_drives(
    new_drives: &Vec<SfaDiskDrive>,
    old_drives: &Vec<SfaDiskDrive>,
    pool: &DbPool,
) -> Result<(), ImlSfaError> {
    let (add, update, remove) = new_drives.get_changes(&old_drives);

    if let Some(add) = add {
        SfaDiskDrive::batch_insert(add).execute_async(pool).await?;
    }

    if let Some(update) = update {
        SfaDiskDrive::batch_upsert(update)
            .execute_async(pool)
            .await?;
    }

    if let Some(remove) = remove {
        let indexes = remove.0.into_iter().map(|x| &x.index).copied().collect();

        SfaDiskDrive::batch_remove(indexes)
            .execute_async(pool)
            .await?;
    }

    Ok(())
}

#[async_trait(?Send)]
trait SfaClassExt: ClientExt {
    async fn fetch_sfa_storage_system(&self, url: Url) -> Result<SfaStorageSystem, ImlSfaError>;
    async fn fetch_sfa_enclosures(&self, url: Url) -> Result<Vec<SfaEnclosure>, ImlSfaError>;
    async fn fetch_sfa_disk_drives(&self, url: Url) -> Result<Vec<SfaDiskDrive>, ImlSfaError>;
}

#[async_trait(?Send)]
impl SfaClassExt for Client {
    async fn fetch_sfa_storage_system(&self, url: Url) -> Result<SfaStorageSystem, ImlSfaError> {
        let x = self
            .get_instance(url, "root/ddn", "DDN_SFAStorageSystem")
            .await?;

        let x: SfaStorageSystem = x.try_into()?;

        Ok(x)
    }
    async fn fetch_sfa_enclosures(&self, url: Url) -> Result<Vec<SfaEnclosure>, ImlSfaError> {
        let x = self.fetch_sfa_storage_system(url.clone());

        let ys = self
            .enumerate_instances(url, "root/ddn", "DDN_SFAEnclosure")
            .err_into();

        let (x, ys) = future::try_join(x, ys).await?;

        let ys = Vec::<Instance>::from(ys)
            .into_iter()
            .map(|y| (x.uuid.clone(), y).try_into())
            .collect::<Result<Vec<_>, _>>()?;

        Ok(ys)
    }
    async fn fetch_sfa_disk_drives(&self, url: Url) -> Result<Vec<SfaDiskDrive>, ImlSfaError> {
        let x = self.fetch_sfa_storage_system(url.clone());

        let ys = self
            .enumerate_instances(url, "root/ddn", "DDN_SFADiskDrive")
            .err_into();

        let (x, ys) = future::try_join(x, ys).await?;

        let ys = Vec::<Instance>::from(ys)
            .into_iter()
            .map(|y| (x.uuid.clone(), y).try_into())
            .collect::<Result<Vec<_>, _>>()?;

        Ok(ys)
    }
}
