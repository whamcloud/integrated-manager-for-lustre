// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::StratagemUpdate;
use bootstrap_components::bs_button;
use futures::Future;
use iml_environment::csrf_token;
use seed::{class, dom_types::At, fetch, i, prelude::*};

#[derive(Debug, Default)]
pub struct Model {
    pub config_data: Option<StratagemUpdate>,
}

#[derive(Clone, Debug)]
pub enum Msg {
    UpdateStratagem,
    StratagemUpdated(fetch::FetchObject<iml_wire_types::Command>),
    OnFetchError(seed::fetch::FailReason),
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut Orders<Msg>) {
    match msg {
        Msg::UpdateStratagem => {
            let orders = orders.skip();

            if let Some(config_data) = &model.config_data {
                orders.perform_cmd(update_stratagem(&config_data));
            }
        }
        Msg::StratagemUpdated(fetch_object) => match fetch_object.response() {
            Ok(response) => {
                log::trace!("Response data: {:#?}", response.data);
                orders.skip();
            }
            Err(fail_reason) => {
                orders.send_msg(Msg::OnFetchError(fail_reason)).skip();
            }
        },
        Msg::OnFetchError(fail_reason) => {
            log::error!("Fetch error: {:#?}", fail_reason);
            orders.skip();
        }
    }

    log::trace!("Model: {:#?}", model);
}

fn update_stratagem(config_data: &StratagemUpdate) -> impl Future<Item = Msg, Error = Msg> {
    let url = format!("/api/stratagem_configuration/{}", config_data.id);

    seed::fetch::Request::new(url)
        .method(seed::fetch::Method::Put)
        .header(
            "X-CSRFToken",
            &csrf_token().expect("Couldn't get csrf token."),
        )
        .send_json(config_data)
        .fetch_json(Msg::StratagemUpdated)
}

pub fn view() -> El<Msg> {
    let mut btn = bs_button::btn(
        class![bs_button::BTN_SUCCESS, "update-button"],
        vec![El::new_text("Update Stratagem"), i![class!["fas fa-check"]]],
    )
    .add_style("grid-column".into(), "2 / span 2".into())
    .add_style("grid-row-end".into(), "5".into());

    btn.listeners
        .push(simple_ev(Ev::Click, Msg::UpdateStratagem));

    btn
}
