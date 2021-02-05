// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use serde::{Deserialize, Serialize};

#[derive(Default, Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SfaSettings {
    pub controllers: Vec<Option<String>>,
    pub password: String,
    pub user: String,
    pub name: String,
}
