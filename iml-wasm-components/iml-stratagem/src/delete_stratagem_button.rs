// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::Command;
use bootstrap_components::bs_button;
use futures::Future;
use iml_environment::csrf_token;
use seed::{class, dom_types::At, i, prelude::*};

pub fn delete_stratagem<T: serde::de::DeserializeOwned + 'static>(
    config_id: u32,
) -> impl Future<Item = seed::fetch::FetchObject<T>, Error = seed::fetch::FetchObject<T>> {
    let url = format!("/api/stratagem_configuration/{}/", config_id);

    seed::fetch::Request::new(url)
        .method(seed::fetch::Method::Delete)
        .header(
            "X-CSRFToken",
            &csrf_token().expect("Couldn't get csrf token."),
        )
        .fetch_json(std::convert::identity)
}

pub fn view(is_valid: bool, disabled: bool) -> Node<Command> {
    let btn = bs_button::btn(
        class![bs_button::BTN_DANGER, "delete-button"],
        vec![Node::new_text("Delete"), i![class!["fas fa-times-circle"]]],
    );

    if is_valid && !disabled {
        btn.add_listener(simple_ev(Ev::Click, Command::Delete))
    } else {
        btn.add_attr(At::Disabled.as_str(), "disabled")
    }
}
