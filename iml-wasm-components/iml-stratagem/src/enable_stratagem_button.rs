// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{Command, StratagemEnable};
use bootstrap_components::bs_button;
use futures::Future;
use iml_environment::csrf_token;
use seed::{class, dom_types::At, i, prelude::*};

pub fn enable_stratagem<T: serde::de::DeserializeOwned + 'static>(
    model: &StratagemEnable,
) -> impl Future<Item = seed::fetch::FetchObject<T>, Error = seed::fetch::FetchObject<T>> {
    seed::fetch::Request::new("/api/stratagem_configuration/")
        .method(seed::fetch::Method::Post)
        .header(
            "X-CSRFToken",
            &csrf_token().expect("Couldn't get csrf token."),
        )
        .send_json(&model)
        .fetch_json(std::convert::identity)
}

pub fn view(is_valid: bool, disabled: bool) -> Node<Command> {
    let btn = bs_button::btn(
        class![bs_button::BTN_PRIMARY],
        vec![
            Node::new_text("Enable Scan Interval"),
            i![class!["far", "fa-clock"]],
        ],
    );

    if is_valid && !disabled {
        btn.add_listener(simple_ev(Ev::Click, Command::Enable))
    } else {
        btn.add_attr(At::Disabled.as_str(), "disabled")
    }
}
