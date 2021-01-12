// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

#[derive(serde::Deserialize, serde::Serialize, Debug, Eq, PartialEq)]
pub struct Response<T> {
    pub exception: Option<String>,
    pub result: Option<T>,
    pub request_id: String,
}
