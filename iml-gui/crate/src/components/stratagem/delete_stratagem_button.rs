// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    auth::csrf_token,
    components::{
        font_awesome_outline,
        stratagem::{Command, StratagemUpdate},
    },
};
use seed::{class, fetch, i, prelude::*, *};

pub async fn delete_stratagem<T: serde::de::DeserializeOwned + 'static>(
    config_id: u32,
) -> Result<fetch::FetchObject<T>, fetch::FetchObject<T>> {
    let url = format!("/api/stratagem_configuration/{}/", config_id);

    seed::fetch::Request::new(url)
        .method(seed::fetch::Method::Delete)
        .header("X-CSRFToken", &csrf_token().expect("Couldn't get csrf token."))
        .fetch_json(std::convert::identity)
        .await
}

pub fn view(is_valid: bool, disabled: bool) -> Node<Command> {
    let mut btn = button!["Delete", i![font_awesome_outline(class![], "fa-times-circle")]];

    if is_valid && !disabled {
        btn.add_listener(simple_ev(Ev::Click, Command::Delete));
    } else {
        btn.add_attr(At::Disabled.as_str(), "disabled");
    }

    btn
}
