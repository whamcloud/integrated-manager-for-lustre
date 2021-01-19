// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use std::collections::HashMap;
use uuid::Uuid;

type Kwargs = HashMap<String, String>;

#[derive(serde::Serialize, serde::Deserialize, Debug)]
pub struct Request {
    request_id: String,
    pub response_routing_key: String,
    args: Vec<String>,
    pub method: String,
    kwargs: Kwargs,
}

impl Request {
    pub fn new<S>(method: S, response_routing_key: S) -> Self
    where
        S: Into<String> + std::cmp::Eq + std::hash::Hash,
    {
        Self {
            request_id: Uuid::new_v4().to_hyphenated().to_string(),
            method: method.into(),
            args: vec![],
            kwargs: HashMap::new(),
            response_routing_key: response_routing_key.into(),
        }
    }
}
