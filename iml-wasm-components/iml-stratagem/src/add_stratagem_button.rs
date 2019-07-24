// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::Future;
use seed::prelude::*;

use seed::{attrs, button, class, dom_types::At, fetch, log, style};

/// Record from the `chroma_core_stratagemconfiguration` table
#[derive(serde::Serialize)]
struct UnconfiguredStratagemConfiguration {
    pub filesystem: u32,
    pub interval: u64,
}

#[derive(Debug, Default)]
pub struct Model {
    pub fs_id: u32,
    pub destroyed: bool,
}

// Update
#[derive(Clone, Debug)]
pub enum Msg {
    Destroy,
    AddStratagem,
    StratagemAdded(fetch::FetchObject<iml_wire_types::Command>),
    OnFetchError(seed::fetch::FailReason),
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut Orders<Msg>) {
    match msg {
        Msg::Destroy => model.destroyed = true,
        Msg::AddStratagem => {
            orders.skip().perform_cmd(add_stratagem(model.fs_id));
        }
        Msg::StratagemAdded(fetch_object) => match fetch_object.response() {
            Ok(response) => {
                log!(format!("Response data: {:#?}", response.data));
                orders.skip();
            }
            Err(fail_reason) => {
                orders.send_msg(Msg::OnFetchError(fail_reason)).skip();
            }
        },
        Msg::OnFetchError(fail_reason) => {
            log!(format!("Fetch error: {:#?}", fail_reason));
            orders.skip();
        }
    }

    log::trace!("Model: {:#?}", model);
}

fn add_stratagem(filesystem_id: u32) -> impl Future<Item = Msg, Error = Msg> {
    let url: String = "/api/stratagem_configuration/".into();
    let config = UnconfiguredStratagemConfiguration {
        filesystem: filesystem_id,
        interval: 2_592_000_000,
    };

    seed::fetch::Request::new(url)
        .method(seed::fetch::Method::Post)
        .send_json(&config)
        .fetch_json(Msg::StratagemAdded)
}

// View
pub fn view(_model: &Model) -> El<Msg> {
    button![
        class!["btn btn-primary"],
        attrs! {
            At::Type => "button",
        },
        style! {
            "grid-column" => "1 / span 3",
            "grid-row-end" => "5"
        },
        simple_ev(Ev::Click, Msg::AddStratagem),
        "Enable Stratagem",
    ]
}
