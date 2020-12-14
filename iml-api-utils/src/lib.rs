// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.
pub mod dependency_tree;
pub mod diff;
pub mod gen_tree;

use lazy_static::lazy_static;
use regex::Regex;

/// Given a resource_uri, attempts to parse the id from it
pub fn extract_id(s: &str) -> Option<&str> {
    lazy_static! {
        static ref RE: Regex = Regex::new(r"^/?api/[^/]+/(\d+)/?$").unwrap();
    }
    let x = RE.captures(s)?;

    x.get(1).map(|x| x.as_str())
}
