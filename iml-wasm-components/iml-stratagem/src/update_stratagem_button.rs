// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{Command, StratagemUpdate};
use bootstrap_components::bs_button;
use futures::Future;
use iml_environment::csrf_token;
use seed::{class, dom_types::At, i, prelude::*};

pub fn update_stratagem<T: serde::de::DeserializeOwned + 'static>(
    config_data: &StratagemUpdate,
) -> impl Future<Item = seed::fetch::FetchObject<T>, Error = seed::fetch::FetchObject<T>> {
    let url = format!("/api/stratagem_configuration/{}/", config_data.id);

    seed::fetch::Request::new(url)
        .method(seed::fetch::Method::Put)
        .header(
            "X-CSRFToken",
            &csrf_token().expect("Couldn't get csrf token."),
        )
        .send_json(config_data)
        .fetch_json(std::convert::identity)
}

pub fn view(is_valid: bool, disabled: bool) -> Node<Command> {
    let mut btn = bs_button::btn(
        class![bs_button::BTN_SUCCESS, "update-button"],
        vec![Node::new_text("Update"), i![class!["fas fa-check"]]],
    );

    if is_valid && !disabled {
        btn.add_listener(simple_ev(Ev::Click, Command::Update));
    } else {
        btn.add_attr(At::Disabled.as_str(), "disabled");
    }

    btn
}
