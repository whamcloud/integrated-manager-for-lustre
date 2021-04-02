// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use url::Url;

#[derive(Debug, thiserror::Error)]
pub enum Error {
    #[error(transparent)]
    UrlParse(#[from] url::ParseError),
    #[error(transparent)]
    Reqwest(#[from] reqwest::Error),
}

pub fn create(client: reqwest::Client, base_url: Url) -> KumaClient {
    KumaClient { client, base_url }
}

pub struct KumaClient {
    client: reqwest::Client,
    base_url: Url,
}

impl KumaClient {
    pub async fn service_insights(&self) -> Result<List<ServiceInsight>, Error> {
        let xs = self
            .client
            .get(self.base_url.join("service-insights/")?)
            .send()
            .await?
            .error_for_status()?
            .json()
            .await?;

        Ok(xs)
    }
}

#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct List<T> {
    pub total: u32,
    pub items: Vec<T>,
    pub next: Option<String>,
}

#[derive(Default, Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ServiceInsight {
    pub r#type: String,
    pub mesh: String,
    pub name: String,
    pub creation_time: String,
    pub modification_time: String,
    pub status: String,
    pub dataplanes: Dataplanes,
}

#[derive(Default, Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct Dataplanes {
    pub total: u32,
    pub online: Option<u32>,
}
