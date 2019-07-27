// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::Future;
use iml_environment::csrf_token;
use seed::prelude::*;
use seed::{attrs, button, class, dom_types::At, fetch, log, style};

#[derive(Debug, serde::Serialize)]
pub struct UnconfiguredStratagemConfiguration {
    filesystem: u32,
    interval: u64,
}

#[derive(Debug, Default)]
pub struct Model {
    pub fs_id: u32,
    pub disabled: bool,
}

// Update
#[derive(Clone, Debug)]
pub enum Msg {
    EnableStratagem,
    StratagemEnabled(fetch::FetchObject<iml_wire_types::Command>),
    OnFetchError(seed::fetch::FailReason),
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut Orders<Msg>) {
    match msg {
        Msg::EnableStratagem => {
            orders.skip().perform_cmd(enable_stratagem(model.fs_id));
        }
        Msg::StratagemEnabled(fetch_object) => match fetch_object.response() {
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

fn enable_stratagem(filesystem_id: u32) -> impl Future<Item = Msg, Error = Msg> {
    let url: String = "/api/stratagem_configuration/".into();
    let config = UnconfiguredStratagemConfiguration {
        filesystem: filesystem_id,
        interval: 2_592_000_000,
    };

    seed::fetch::Request::new(url)
        .method(seed::fetch::Method::Post)
        .header(
            "X-CSRFToken",
            &csrf_token().expect("Couldn't get csrf token.")[..],
        )
        .send_json(&config)
        .fetch_json(Msg::StratagemEnabled)
}

// View
pub fn view(model: &Model) -> El<Msg> {
    let mut attrs = attrs! {
        At::Type => "button"
    };

    if model.disabled {
        attrs.merge(attrs! {
            At::Disabled => "disabled"
        });
    }

    button![class!["btn btn-primary"], attrs, "Enable Stratagem",]
}
