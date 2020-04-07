// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

mod cim_xml;
pub mod sfa_classes;

pub use cim_xml::{req, resp};

use async_trait::async_trait;
use bytes::buf::ext::BufExt;
use futures::{future, Future, FutureExt, TryFutureExt};
use reqwest::{header, Client, IntoUrl, Response};
use serde::de::DeserializeOwned;
use std::{collections::BTreeMap, iter::FromIterator, pin::Pin, time::Duration};
use thiserror::Error;

#[derive(Error, Debug)]
pub enum WbemClientError {
    #[error("A request error has occured {0}")]
    Reqwest(#[from] reqwest::Error),
    #[error(transparent)]
    InvalidHeaderValue(#[from] header::InvalidHeaderValue),
    #[error(transparent)]
    QuickXmlError(#[from] quick_xml::Error),
    #[error(transparent)]
    QuickXmlDeError(#[from] quick_xml::DeError),
}

/// Get a client that is able to make authenticated requests
/// against the API
pub fn get_client(
    auth: impl Into<Option<(String, String)>>,
    insecure: bool,
) -> Result<Client, WbemClientError> {
    let mut headers = header::HeaderMap::from_iter(vec![(
        header::CONTENT_TYPE,
        header::HeaderValue::from_static("application/xml; charset=\"utf-8\""),
    )]);

    if let Some((k, v)) = auth.into() {
        let x = base64::encode(format!("{}:{}", k, v));
        let x = header::HeaderValue::from_str(&format!("Basic {}", x))?;

        headers.insert(header::AUTHORIZATION, x);
    }

    Client::builder()
        .timeout(Duration::from_secs(60))
        .default_headers(headers)
        .danger_accept_invalid_certs(insecure)
        .build()
        .map_err(WbemClientError::Reqwest)
}

pub trait ClientExt {
    /// Perform an intrinsic method call.
    fn imethodcall(
        &self,
        url: impl IntoUrl,
        name: &str,
        namespace: &str,
        params: impl Into<Option<BTreeMap<String, req::ParamValue>>>,
    ) -> Pin<Box<dyn Future<Output = Result<Response, WbemClientError>>>>;
}

impl ClientExt for Client {
    fn imethodcall(
        &self,
        url: impl IntoUrl,
        name: &str,
        namespace: &str,
        params: impl Into<Option<BTreeMap<String, req::ParamValue>>>,
    ) -> Pin<Box<dyn Future<Output = Result<Response, WbemClientError>>>> {
        let namespace_path = namespace
            .split('/')
            .filter(|x| !x.is_empty())
            .map(|x| req::namespace(x))
            .collect::<Vec<_>>();

        let mut local_namespace_path = req::local_namespace_path(namespace_path);

        if let Some(params) = params.into() {
            let mut params = params
                .into_iter()
                .map(|(k, v)| req::iparamvalue(&k, v.into()))
                .flatten()
                .collect();

            local_namespace_path.append(&mut params);
        };

        let xs = req::decl(req::cim(
            "2.0",
            "2.0",
            req::message(
                "1001",
                "1.0",
                req::simple_req(req::imethodcall(name, local_namespace_path)),
            ),
        ));

        let req = self
            .post(url)
            .header("CIMOperation", "MethodCall")
            .header("CIMMethod", name)
            .header("CIMObject", namespace);

        future::ready(req::evs_to_bytes(xs))
            .err_into()
            .and_then(|body| req.body(body).send().err_into())
            .boxed()
    }
}

#[async_trait]
pub trait ResponseExt {
    /// Try to deserialize the response body as XML
    async fn xml<T: DeserializeOwned>(self) -> Result<T, WbemClientError>;
}

#[async_trait]
impl ResponseExt for Response {
    async fn xml<T: DeserializeOwned>(self) -> Result<T, WbemClientError> {
        let full = self.bytes().await?;

        quick_xml::de::from_reader(&mut full.reader()).map_err(WbemClientError::QuickXmlDeError)
    }
}
