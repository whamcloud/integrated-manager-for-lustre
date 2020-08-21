// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::ImlSfaError;
use async_trait::async_trait;
use futures::{future, TryFutureExt};
use iml_wire_types::sfa::wbem_interop::{
    SfaController, SfaDiskDrive, SfaEnclosure, SfaJob, SfaPowerSupply, SfaStorageSystem,
};
use std::convert::TryInto as _;
use url::Url;
use wbem_client::{resp::Instance, Client, ClientExt};

#[async_trait(?Send)]
pub trait SfaClassExt: ClientExt {
    async fn fetch_sfa_storage_system(&self, url: Url) -> Result<SfaStorageSystem, ImlSfaError>;
    async fn fetch_sfa_enclosures(&self, url: Url) -> Result<Vec<SfaEnclosure>, ImlSfaError>;
    async fn fetch_sfa_disk_drives(&self, url: Url) -> Result<Vec<SfaDiskDrive>, ImlSfaError>;
    async fn fetch_sfa_jobs(&self, url: Url) -> Result<Vec<SfaJob>, ImlSfaError>;
    async fn fetch_sfa_power_supply(&self, url: Url) -> Result<Vec<SfaPowerSupply>, ImlSfaError>;
    async fn fetch_sfa_controllers(&self, url: Url) -> Result<Vec<SfaController>, ImlSfaError>;
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
    async fn fetch_sfa_jobs(&self, url: Url) -> Result<Vec<SfaJob>, ImlSfaError> {
        let x = self.fetch_sfa_storage_system(url.clone());

        let ys = self
            .enumerate_instances(url, "root/ddn", "DDN_SFAJob")
            .err_into();

        let (x, ys) = future::try_join(x, ys).await?;

        let ys = Vec::<Instance>::from(ys)
            .into_iter()
            .map(|y| (x.uuid.clone(), y).try_into())
            .collect::<Result<Vec<_>, _>>()?;

        Ok(ys)
    }
    async fn fetch_sfa_power_supply(&self, url: Url) -> Result<Vec<SfaPowerSupply>, ImlSfaError> {
        let x = self.fetch_sfa_storage_system(url.clone());

        let ys = self
            .enumerate_instances(url, "root/ddn", "DDN_SFAPowerSupply")
            .err_into();

        let (x, ys) = future::try_join(x, ys).await?;

        let ys = Vec::<Instance>::from(ys)
            .into_iter()
            .map(|y| (x.uuid.clone(), y).try_into())
            .collect::<Result<Vec<_>, _>>()?;

        Ok(ys)
    }
    async fn fetch_sfa_controllers(&self, url: Url) -> Result<Vec<SfaController>, ImlSfaError> {
        let x = self.fetch_sfa_storage_system(url.clone());

        let ys = self
            .enumerate_instances(url, "root/ddn", "DDN_SFAController")
            .err_into();

        let (x, ys) = future::try_join(x, ys).await?;

        let ys = Vec::<Instance>::from(ys)
            .into_iter()
            .map(|y| (x.uuid.clone(), y).try_into())
            .collect::<Result<Vec<_>, _>>()?;

        Ok(ys)
    }
}
