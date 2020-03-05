// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    auth::csrf_token,
    components::{
        font_awesome_outline,
        stratagem::{Command, StratagemEnable},
    },
    extensions::MergeAttrs,
    generated::css_classes::C,
};
use seed::{fetch, i, prelude::*, *};

pub async fn enable_stratagem<T: serde::de::DeserializeOwned + 'static>(
    model: StratagemEnable,
) -> Result<fetch::FetchObject<T>, fetch::FetchObject<T>> {
    log!("enable with", model);
    fetch::Request::new("/api/stratagem_configuration/")
        .method(fetch::Method::Post)
        .header("X-CSRFToken", &csrf_token().expect("Couldn't get csrf token."))
        .send_json(&model)
        .fetch_json(std::convert::identity)
        .await
}

pub fn view(is_valid: bool, disabled: bool) -> Node<Command> {
    let cls = class![
        C.bg_blue_500,
        C.hover__bg_blue_700,
        C.text_white,
        C.font_bold,
        C.py_2,
        C.px_2,
        C.rounded,
        C.w_full,
        C.text_sm
    ];

    let mut btn = button![
        cls,
        "Enable Scan Interval",
        i![
            class![C.px_3],
            font_awesome_outline(class![C.inline, C.h_4, C.w_4], "clock")
        ]
    ];

    if is_valid && !disabled {
        btn.add_listener(simple_ev(Ev::Click, Command::Enable));
    } else {
        btn = btn
            .merge_attrs(attrs! {At::Disabled => "disabled"})
            .merge_attrs(class![C.opacity_50, C.cursor_not_allowed]);
    }

    btn
}
