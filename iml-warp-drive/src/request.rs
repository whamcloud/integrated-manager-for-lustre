// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::future::Future;

use serde_json;
use std::collections::HashMap;
use uuid::Uuid;

use crate::TcpChannel;

type Kwargs = HashMap<String, String>;

#[derive(serde_derive::Serialize, serde_derive::Deserialize, Debug)]
pub struct Request {
    request_id: String,
    pub response_routing_key: String,
    args: Vec<String>,
    pub method: String,
    kwargs: Kwargs,
}

impl Request {
    pub fn new<S>(method: S, response_routing_key: S) -> Request
    where
        S: Into<String> + std::cmp::Eq + std::hash::Hash,
    {
        Request {
            request_id: Uuid::new_v4().to_hyphenated().to_string(),
            method: method.into(),
            args: vec![],
            kwargs: HashMap::new(),
            response_routing_key: response_routing_key.into(),
        }
    }
    pub fn to_vec(&self) -> Vec<u8> {
        serde_json::to_vec(self).unwrap()
    }
}

impl From<Request> for Vec<u8> {
    fn from(req: Request) -> Self {
        req.to_vec()
    }
}

pub trait TcpChannelFuture: Future<Item = TcpChannel, Error = failure::Error> {}
impl<T: Future<Item = TcpChannel, Error = failure::Error>> TcpChannelFuture for T {}
