// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use std::collections::HashMap;
use uuid::Uuid;

type Kwargs = HashMap<String, String>;

#[derive(serde::Serialize, serde::Deserialize, Debug)]
pub struct Request<T> {
    pub(crate) request_id: String,
    pub response_routing_key: String,
    args: Vec<T>,
    pub method: String,
    kwargs: Kwargs,
}

impl<T> Request<T> {
    pub fn new(
        method: impl Into<String>,
        response_routing_key: impl Into<String>,
        args: Vec<T>,
        kwargs: Kwargs,
    ) -> Self {
        Self {
            request_id: Uuid::new_v4().to_hyphenated().to_string(),
            method: method.into(),
            args,
            kwargs,
            response_routing_key: response_routing_key.into(),
        }
    }
}
