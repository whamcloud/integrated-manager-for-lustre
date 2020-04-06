// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use std::collections::HashMap;

pub mod filesystem;
pub mod filesystems;

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
