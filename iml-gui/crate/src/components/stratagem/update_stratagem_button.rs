// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    auth::csrf_token,
    components::{
        font_awesome_outline,
        stratagem::{Command, StratagemUpdate},
    },
    extensions::MergeAttrs,
    generated::css_classes::C,
};
use seed::{class, fetch, i, prelude::*, *};

pub async fn update_stratagem<T: serde::de::DeserializeOwned + 'static>(
    config_data: StratagemUpdate,
) -> Result<fetch::FetchObject<T>, fetch::FetchObject<T>> {
    let url = format!("/api/stratagem_configuration/{}/", config_data.id);

    fetch::Request::new(url)
        .method(fetch::Method::Put)
        .header("X-CSRFToken", &csrf_token().expect("Couldn't get csrf token."))
        .send_json(&config_data)
        .fetch_json(std::convert::identity)
        .await
}

pub fn view(is_valid: bool, disabled: bool) -> Node<Command> {
    let cls = class![
        C.bg_green_500,
        C.hover__bg_green_700,
        C.text_white,
        C.font_bold,
        C.py_2,
        C.px_2,
        C.rounded,
        C.w_full,
        C.text_sm,
        C.col_span_2,
    ];

    let mut btn = button![
        cls,
        "Update",
        i![
            class![C.px_3],
            font_awesome_outline(class![C.inline, C.h_4, C.w_4], "check-circle")
        ]
    ];

    if is_valid && !disabled {
        btn.add_listener(simple_ev(Ev::Click, Command::Update));
    } else {
        btn = btn
            .merge_attrs(attrs! {At::Disabled => "disabled"})
            .merge_attrs(class![C.opacity_50, C.cursor_not_allowed]);
    }

    btn
}
