// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    components::{
        font_awesome_outline,
        stratagem::{Command, StratagemEnable},
    },
    extensions::{MergeAttrs, NodeExt, RequestExt},
    generated::css_classes::C,
};
use emf_wire_types::{EndpointName, StratagemConfiguration};
use seed::{prelude::*, *};

pub async fn enable_stratagem<T: serde::de::DeserializeOwned + 'static>(
    model: StratagemEnable,
) -> Result<fetch::FetchObject<T>, fetch::FetchObject<T>> {
    fetch::Request::api_call(StratagemConfiguration::endpoint_name())
        .method(fetch::Method::Post)
        .with_auth()
        .send_json(&model)
        .fetch_json(std::convert::identity)
        .await
}

pub fn view(is_valid: bool, disabled: bool) -> Node<Command> {
    let btn = button![
        class![
            C.bg_blue_500,
            C.hover__bg_blue_700,
            C.text_white,
            C.font_bold,
            C.p_2,
            C.rounded,
            C.w_full,
            C.text_sm,
            C.col_span_2,
        ],
        "Enable Scan Interval",
        font_awesome_outline(class![C.inline, C.h_4, C.w_4, C.ml_2], "clock")
    ];

    if is_valid && !disabled {
        btn.with_listener(simple_ev(Ev::Click, Command::Enable))
    } else {
        btn.merge_attrs(attrs! {At::Disabled => "disabled"})
            .merge_attrs(class![C.opacity_50, C.cursor_not_allowed])
    }
}
