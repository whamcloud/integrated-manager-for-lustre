// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    components::{panel, resource_links, table},
    generated::css_classes::C,
    route::{Route, RouteId},
};
use emf_wire_types::{
    db::{AuthGroupRecord, AuthUserRecord},
    warp_drive::ArcCache,
};
use seed::{prelude::*, *};
use std::sync::Arc;

#[derive(Clone, Debug)]
pub enum Msg {}

fn full_name(x: &AuthUserRecord) -> String {
    match (x.first_name.as_str(), x.last_name.as_str()) {
        ("", "") => "---".into(),
        ("", x) => x.into(),
        (x, "") => x.into(),
        (x, y) => format!("{} {}", x, y),
    }
}

fn empty_to_dash(x: &str) -> String {
    if x.is_empty() {
        "---".into()
    } else {
        x.into()
    }
}

fn user_to_group<'a>(x: &AuthUserRecord, cache: &'a ArcCache) -> Option<&'a Arc<AuthGroupRecord>> {
    let ug = cache.user_group.values().find(|y| y.user_id == x.id)?;

    cache.group.get(&ug.group_id)
}

pub fn view(cache: &ArcCache) -> Node<Msg> {
    panel::view(
        h3![class![C.py_4, C.font_normal, C.text_lg], "Users"],
        table::wrapper_view(vec![
            table::thead_view(vec![
                table::th_view(plain!["Username"]),
                table::th_view(plain!["Name"]),
                table::th_view(plain!["Email"]),
                table::th_view(plain!["Role"]),
            ]),
            tbody![cache.user.values().map(|x| {
                tr![
                    table::td_view(resource_links::href_view(&x.username, Route::User(RouteId::from(x.id)))),
                    table::td_view(plain![full_name(x)]),
                    table::td_view(plain![empty_to_dash(&x.email)]),
                    table::td_view(match user_to_group(x, cache) {
                        Some(y) => plain![y.name.to_string()],
                        None => plain!["---"],
                    })
                ]
            })],
        ]),
    )
}
