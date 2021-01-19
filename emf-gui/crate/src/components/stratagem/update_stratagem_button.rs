// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    components::{
        font_awesome_outline,
        stratagem::{Command, StratagemUpdate},
    },
    extensions::{MergeAttrs, NodeExt, RequestExt},
    generated::css_classes::C,
};
use emf_wire_types::{EndpointName, StratagemConfiguration};
use seed::{prelude::*, *};

pub async fn update_stratagem<T: serde::de::DeserializeOwned + 'static>(
    config_data: StratagemUpdate,
) -> Result<fetch::FetchObject<T>, fetch::FetchObject<T>> {
    fetch::Request::api_item(StratagemConfiguration::endpoint_name(), config_data.id)
        .method(fetch::Method::Put)
        .with_auth()
        .send_json(&config_data)
        .fetch_json(std::convert::identity)
        .await
}

pub fn view(is_valid: bool, disabled: bool) -> Node<Command> {
    let btn = button![
        class![
            C.bg_green_500,
            C.hover__bg_green_700,
            C.text_white,
            C.font_bold,
            C.p_2,
            C.rounded,
            C.w_full,
            C.text_sm,
            C.col_span_2,
        ],
        "Update",
        font_awesome_outline(class![C.inline, C.h_4, C.w_4, C.px_3], "check-circle")
    ];

    if is_valid && !disabled {
        btn.with_listener(simple_ev(Ev::Click, Command::Update))
    } else {
        btn.merge_attrs(attrs! {At::Disabled => "disabled"})
            .merge_attrs(class![C.opacity_50, C.cursor_not_allowed])
    }
}
