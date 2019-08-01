// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::StratagemScan;
use bootstrap_components::bs_button;
use futures::Future;
use iml_environment::csrf_token;
use iml_utils::dispatch_custom_event::dispatch_custom_event;
use seed::{class, dom_types::At, fetch, prelude::*};

#[derive(Debug, Default)]
pub struct Model {
    pub config_data: Option<StratagemScan>,
}

#[derive(Clone, Debug)]
pub enum Msg {
    ScanStratagem,
    StratagemScanned(fetch::FetchObject<iml_wire_types::Command>),
    OnFetchError(seed::fetch::FailReason),
}

pub fn scan(msg: Msg, model: &mut Model, orders: &mut Orders<Msg>) {
    match msg {
        Msg::ScanStratagem => {
            let orders = orders.skip();

            if let Some(config_data) = &model.config_data {
                orders.perform_cmd(scan_stratagem(&config_data));
                dispatch_custom_event("show_command_modal", &model.config_data);
            }
        }
        Msg::StratagemScanned(fetch_object) => match fetch_object.response() {
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

fn scan_stratagem(config_data: &StratagemScan) -> impl Future<Item = Msg, Error = Msg> {
    let url = format!("/api/run_stratagem/");

    seed::fetch::Request::new(url)
        .method(seed::fetch::Method::Post)
        .header(
            "X-CSRFToken",
            &csrf_token().expect("Couldn't get csrf token."),
        )
        .send_json(config_data)
        .fetch_json(Msg::StratagemScanned)
}

pub fn view() -> El<Msg> {
    let mut btn = bs_button::btn(
        class![bs_button::BTN_PRIMARY, "scan-button"],
        vec![El::new_text("Scan Stratagem")],
    );

    btn.listeners.push(simple_ev(Ev::Click, Msg::ScanStratagem));

    btn
}
