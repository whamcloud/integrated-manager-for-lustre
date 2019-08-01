// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use bootstrap_components::bs_button;
use futures::Future;
use iml_environment::csrf_token;
use iml_utils::dispatch_custom_event::dispatch_custom_event;
use seed::{class, dom_types::At, fetch, prelude::*};

#[derive(Debug, serde::Serialize)]
pub struct Model {
    pub filesystem: u32,
    pub interval: u64,
    pub report_duration: Option<u64>,
    pub purge_duration: Option<u64>,
}

#[derive(Clone, Debug)]
pub enum Msg {
    EnableStratagem,
    StratagemEnabled(fetch::FetchObject<iml_wire_types::Command>),
    OnFetchError(seed::fetch::FailReason),
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut Orders<Msg>) {
    let orders = orders.skip();

    match msg {
        Msg::EnableStratagem => {
            orders.perform_cmd(enable_stratagem(&model));
            dispatch_custom_event("show_command_modal", &model);
        }
        Msg::StratagemEnabled(fetch_object) => match fetch_object.response() {
            Ok(response) => {
                log::trace!("Response data: {:#?}", response.data);
            }
            Err(fail_reason) => {
                orders.send_msg(Msg::OnFetchError(fail_reason));
            }
        },
        Msg::OnFetchError(fail_reason) => {
            log::warn!("Fetch error: {:#?}", fail_reason);
        }
    }

    log::trace!("Model: {:#?}", model);
}

fn enable_stratagem(model: &Model) -> impl Future<Item = Msg, Error = Msg> {
    let url = "/api/stratagem_configuration/".into();

    seed::fetch::Request::new(url)
        .method(seed::fetch::Method::Post)
        .header(
            "X-CSRFToken",
            &csrf_token().expect("Couldn't get csrf token."),
        )
        .send_json(model)
        .fetch_json(Msg::StratagemEnabled)
}

pub fn view(model: &Option<Model>) -> El<Msg> {
    let mut btn = bs_button::btn(
        class![bs_button::BTN_PRIMARY],
        vec![El::new_text("Enable Stratagem")],
    );

    if model.is_some() {
        btn.listeners
            .push(simple_ev(Ev::Click, Msg::EnableStratagem));

        btn
    } else {
        btn.add_attr(At::Disabled.as_str().into(), "disabled".into())
    }
}
