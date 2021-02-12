// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

mod cim_xml;

use async_trait::async_trait;
use bytes::Buf;
pub use cim_xml::{
    CimXmlError, {req, resp},
};
use emf_tracing::tracing;
use futures::{future, Future, FutureExt, TryFutureExt};
pub use reqwest::Client;
use reqwest::{header, IntoUrl, Response};
use resp::{Cim, IReturnValueInstance, IReturnValueNamedInstance};
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
pub fn get_client(insecure: bool) -> Result<Client, WbemClientError> {
    let headers = header::HeaderMap::from_iter(vec![(
        header::CONTENT_TYPE,
        header::HeaderValue::from_static("application/xml; charset=\"utf-8\""),
    )]);

    Client::builder()
        .timeout(Duration::from_secs(60))
        .default_headers(headers)
        .danger_accept_invalid_certs(insecure)
        .build()
        .map_err(WbemClientError::Reqwest)
}

pub trait ClientExt {
    fn enumerate_instances(
        &self,
        url: impl IntoUrl,
        namespace: &str,
        class_name: &str,
    ) -> Pin<Box<dyn Future<Output = Result<Cim<IReturnValueNamedInstance>, WbemClientError>>>>;
    fn get_instance(
        &self,
        url: impl IntoUrl,
        namespace: &str,
        instance_name: &str,
    ) -> Pin<Box<dyn Future<Output = Result<Cim<IReturnValueInstance>, WbemClientError>>>>;
    /// Perform an intrinsic method call.
    fn imethodcall<T: serde::de::DeserializeOwned + 'static>(
        &self,
        url: impl IntoUrl,
        name: &str,
        namespace: &str,
        params: impl Into<Option<BTreeMap<String, req::ParamValue>>>,
    ) -> Pin<Box<dyn Future<Output = Result<Cim<T>, WbemClientError>>>>;
}

impl ClientExt for Client {
    fn enumerate_instances(
        &self,
        url: impl IntoUrl,
        namespace: &str,
        class_name: &str,
    ) -> Pin<Box<dyn Future<Output = Result<Cim<IReturnValueNamedInstance>, WbemClientError>>>>
    {
        let params: BTreeMap<String, _> = BTreeMap::from_iter(vec![(
            "ClassName".into(),
            req::ParamValue::ClassName(class_name.into()),
        )]);

        self.imethodcall(url, "EnumerateInstances", namespace, params)
    }
    fn get_instance(
        &self,
        url: impl IntoUrl,
        namespace: &str,
        instance_name: &str,
    ) -> Pin<Box<dyn Future<Output = Result<Cim<IReturnValueInstance>, WbemClientError>>>> {
        let params: BTreeMap<String, _> = BTreeMap::from_iter(vec![(
            "InstanceName".into(),
            req::ParamValue::InstanceName(instance_name.into()),
        )]);

        self.imethodcall(url, "GetInstance", namespace, params)
    }
    fn imethodcall<T: serde::de::DeserializeOwned + 'static>(
        &self,
        url: impl IntoUrl,
        name: &str,
        namespace: &str,
        params: impl Into<Option<BTreeMap<String, req::ParamValue>>>,
    ) -> Pin<Box<dyn Future<Output = Result<Cim<T>, WbemClientError>>>> {
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

        tracing::debug!(wbem_req = ?xs);

        let req = self
            .post(url)
            .header("CIMOperation", "MethodCall")
            .header("CIMMethod", name)
            .header("CIMObject", namespace);

        future::ready(req::evs_to_bytes(xs))
            .err_into()
            .and_then(|body| req.body(body).send().err_into())
            .and_then(|resp| async {
                let x = resp.error_for_status()?;

                Ok(x)
            })
            .and_then(|x| x.xml::<Cim<T>>().err_into())
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

        tracing::trace!(xml = ?full);

        quick_xml::de::from_reader(&mut full.reader()).map_err(WbemClientError::QuickXmlDeError)
    }
}
