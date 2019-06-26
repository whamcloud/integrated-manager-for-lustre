// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use seed::document;

pub fn ui_root() -> String {
    document().base_uri().unwrap().unwrap_or_default()
}
