// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

#[derive(serde::Deserialize, serde::Serialize, Debug)]
pub struct LinkEA {
    pub pfid: String,
    pub name: String,
}

#[derive(serde::Deserialize, serde::Serialize, Debug)]
pub struct FidListItem {
    pub fid: String,
    pub linkea: Vec<LinkEA>,
}

impl FidListItem {
    pub fn new(fid: String) -> Self {
        FidListItem {
            fid,
            linkea: vec![],
        }
    }
}
