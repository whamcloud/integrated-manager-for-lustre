// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{ActionResponse, StratagemUpdate};
use bootstrap_components::bs_button;
use futures::Future;
use iml_environment::csrf_token;
use iml_utils::dispatch_custom_event;
use seed::{class, dom_types::At, fetch, i, prelude::*};

#[derive(Debug, Default)]
pub struct Model {
    pub config_data: Option<StratagemUpdate>,
    pub disabled: bool,
}

#[derive(Clone, Debug)]
pub enum Msg {
    UpdateStratagem,
    StratagemUpdated(fetch::FetchObject<ActionResponse>),
    OnFetchError(seed::fetch::FailReason<ActionResponse>),
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg>) {
    match msg {
        Msg::UpdateStratagem => {
            model.disabled = true;
            if let Some(config_data) = &model.config_data {
                orders.perform_cmd(update_stratagem(&config_data));
            }
        }
        Msg::StratagemUpdated(fetch_object) => match fetch_object.response() {
            Ok(response) => {
                log::trace!("Response data: {:#?}", response.data);
                dispatch_custom_event("show_command_modal", &response.data);
                model.disabled = false;
                orders.skip();
            }
            Err(fail_reason) => {
                orders.send_msg(Msg::OnFetchError(fail_reason)).skip();
            }
        },
        Msg::OnFetchError(fail_reason) => {
            model.disabled = false;
            log::error!("Fetch error: {:#?}", fail_reason);
        }
    }

    log::trace!("Model: {:#?}", model);
}

fn update_stratagem(config_data: &StratagemUpdate) -> impl Future<Item = Msg, Error = Msg> {
    let url = format!("/api/stratagem_configuration/{}/", config_data.id);

    seed::fetch::Request::new(url)
        .method(seed::fetch::Method::Put)
        .header(
            "X-CSRFToken",
            &csrf_token().expect("Couldn't get csrf token."),
        )
        .send_json(config_data)
        .fetch_json(Msg::StratagemUpdated)
}

pub fn view(is_valid: bool) -> Node<Msg> {
    let mut btn = bs_button::btn(
        class![bs_button::BTN_SUCCESS, "update-button"],
        vec![Node::new_text("Update"), i![class!["fas fa-check"]]],
    )
    .add_listener(simple_ev(Ev::Click, Msg::UpdateStratagem));

    if !is_valid {
        btn = btn.add_attr(At::Disabled.as_str(), "disabled");
    }

    btn
}
