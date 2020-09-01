// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use std::collections::HashMap;

pub mod filesystem;
pub mod filesystems;

use serde_json::{Map, Value};

#[derive(serde::Deserialize, Clone, Debug)]
pub struct InfluxResponse<T> {
    results: Vec<InfluxResult<T>>,
}

#[derive(serde::Deserialize, Clone, Debug)]
pub struct InfluxResult<T> {
    series: Option<Vec<InfluxSeries<T>>>,
}

#[derive(serde::Deserialize, Clone, Debug)]
pub struct InfluxSeries<T> {
    tags: Option<HashMap<String, String>>,
    values: Vec<T>,
}

pub struct ColVals(pub Vec<String>, pub Vec<Vec<serde_json::Value>>);

impl From<ColVals> for serde_json::Value {
    fn from(ColVals(cols, vals): ColVals) -> Self {
        let xs = vals
            .into_iter()
            .map(|y| -> Map<String, serde_json::Value> {
                cols.clone().into_iter().zip(y).collect()
            })
            .map(Value::Object)
            .collect();

        Value::Array(xs)
    }
}
