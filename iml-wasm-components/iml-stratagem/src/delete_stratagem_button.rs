// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::Future;
use iml_environment::csrf_token;
use seed::prelude::*;
use seed::{attrs, button, class, dom_types::At, fetch, log, style};

#[derive(Debug, Default)]
pub struct Model {
    pub config_id: u32,
}

// Update
#[derive(Clone, Debug)]
pub enum Msg {
    DeleteStratagem,
    StratagemDeleted(fetch::FetchObject<iml_wire_types::Command>),
    OnFetchError(seed::fetch::FailReason),
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut Orders<Msg>) {
    match msg {
        Msg::DeleteStratagem => {
            orders.skip().perform_cmd(delete_stratagem(model.config_id));
        }
        Msg::StratagemDeleted(fetch_object) => match fetch_object.response() {
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

fn delete_stratagem(config_id: u32) -> impl Future<Item = Msg, Error = Msg> {
    let url: String = format!("/api/stratagem_configuration/{}", config_id).into();

    seed::fetch::Request::new(url)
        .method(seed::fetch::Method::Delete)
        .header(
            "X-CSRFToken",
            &csrf_token().expect("Couldn't get csrf token.")[..],
        )
        .fetch_json(Msg::StratagemDeleted)
}

// View
pub fn view(_model: &Model) -> El<Msg> {
    button![
        class!["btn btn-danger delete-button"],
        attrs! {
            At::Type => "button",
        },
        style! {
            "grid-column" => "1",
            "grid-row-end" => "5"
        },
        simple_ev(Ev::Click, Msg::DeleteStratagem),
        "Delete Stratagem",
    ]
}
