// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{extensions::MergeAttrs as _, generated::css_classes::C, route::RouteId, Route};
use emf_api_utils::extract_id;
use emf_wire_types::Filesystem;
use seed::{prelude::*, *};

pub fn href_view<T>(x: &str, route: Route) -> Node<T> {
    a![
        class![C.text_blue_500, C.hover__underline],
        attrs! {At::Href => route.to_href()},
        x
    ]
}

pub fn label_view<T>(x: &str, _: Route) -> Node<T> {
    span![x]
}

pub fn server_link<T>(uri: Option<&String>, txt: &str) -> Node<T> {
    if let Some(u) = uri {
        let srv_id = extract_id(u).unwrap();

        href_view(txt, Route::Server(RouteId::from(srv_id))).merge_attrs(class![C.block])
    } else {
        plain!["---"]
    }
}

pub fn fs_link<T>(x: &Filesystem) -> Node<T> {
    href_view(&x.name, Route::Filesystem(RouteId::from(x.id))).merge_attrs(class![C.break_all])
}
