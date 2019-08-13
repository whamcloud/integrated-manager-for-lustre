// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use bootstrap_components::bs_button;
use futures::Future;
use iml_environment::csrf_token;
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
    OnFetchError(seed::fetch::FailReason<iml_wire_types::Command>),
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg>) {
    let orders = orders.skip();

    match msg {
        Msg::EnableStratagem => {
            orders.perform_cmd(enable_stratagem(&model));
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
}

fn enable_stratagem(model: &Model) -> impl Future<Item = Msg, Error = Msg> {
    seed::fetch::Request::new("/api/stratagem_configuration/")
        .method(seed::fetch::Method::Post)
        .header(
            "X-CSRFToken",
            &csrf_token().expect("Couldn't get csrf token."),
        )
        .send_json(model)
        .fetch_json(Msg::StratagemEnabled)
}

pub fn view(model: &Option<Model>) -> Node<Msg> {
    let btn = bs_button::btn(
        class![bs_button::BTN_PRIMARY],
        vec![Node::new_text("Enable Interval")],
    );

    if model.is_some() {
        btn.add_listener(simple_ev(Ev::Click, Msg::EnableStratagem))
    } else {
        btn.add_attr(At::Disabled.as_str(), "disabled")
    }
}
