// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::StratagemUpdate;
use futures::Future;
use iml_environment::csrf_token;
use seed::prelude::*;
use seed::{attrs, button, class, dom_types::At, fetch, log, style};

#[derive(Debug, Default)]
pub struct Model {
  pub config_data: Option<StratagemUpdate>,
}

// Update
#[derive(Clone, Debug)]
pub enum Msg {
  UpdateStratagem,
  StratagemUpdated(fetch::FetchObject<iml_wire_types::Command>),
  OnFetchError(seed::fetch::FailReason),
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut Orders<Msg>) {
  match msg {
    Msg::UpdateStratagem => {
      if let Some(config_data) = model.config_data.clone() {
        orders.skip().perform_cmd(update_stratagem(config_data));
      } else {
        orders.skip();
      }
    }
    Msg::StratagemUpdated(fetch_object) => match fetch_object.response() {
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

fn update_stratagem(config_data: StratagemUpdate) -> impl Future<Item = Msg, Error = Msg> {
  let url: String = format!("/api/stratagem_configuration/{}", config_data.id).into();

  seed::fetch::Request::new(url)
    .method(seed::fetch::Method::Put)
    .header(
      "X-CSRFToken",
      &csrf_token().expect("Couldn't get csrf token.")[..],
    )
    .send_json(&config_data)
    .fetch_json(Msg::StratagemUpdated)
}

// View
pub fn view(_model: &Model) -> El<Msg> {
  button![
    class!["btn btn-success update-button"],
    attrs! {
        At::Type => "button",
    },
    style! {
        "grid-column" => "2 / span 2",
        "grid-row-end" => "5"
    },
    simple_ev(Ev::Click, Msg::UpdateStratagem),
    "Update Stratagem",
  ]
}
