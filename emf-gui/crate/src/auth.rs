// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{sleep_with_handle, FailReasonExt, GMsg, RequestExt, Route, SessionExt};
use emf_wire_types::{EndpointName, Session};
use futures::channel::oneshot;
use regex::Regex;
use seed::{browser::service::fetch, prelude::*, *};
use std::time::Duration;
use wasm_bindgen::JsValue;
use web_sys::HtmlDocument;

#[derive(Default)]
pub struct Model {
    session: Option<Session>,
    request_controller: Option<fetch::RequestController>,
    cancel: Option<oneshot::Sender<()>>,
}

impl Model {
    pub(crate) fn get_session(&self) -> Option<&Session> {
        self.session.as_ref()
    }
}

#[allow(clippy::large_enum_variant)]
#[derive(Clone, Debug)]
pub enum Msg {
    Fetch,
    Fetched(fetch::FetchObject<Session>),
    Logout,
    LoggedIn,
    Loop,
    Noop,
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::Fetch => {
            model.cancel = None;

            let request = fetch_session().controller(|controller| model.request_controller = Some(controller));

            orders.skip().perform_cmd(request.fetch_json(Msg::Fetched));
        }
        Msg::Fetched(data) => {
            match data.response() {
                Err(fail_reason) => {
                    log!(format!("Error during session poll: {}", fail_reason.message()));
                    orders.skip().send_msg(Msg::Loop);
                }
                Ok(resp) => {
                    model.session = Some(resp.data);

                    if model.session.as_ref().unwrap().needs_login() {
                        orders.send_g_msg(GMsg::RouteChange(Route::Login.into()));
                    } else {
                        orders.send_msg(Msg::Loop);
                    }

                    resp.raw
                        .headers()
                        .get("date")
                        .map_err(|j| error!(j))
                        .ok()
                        .flatten()
                        .and_then(|h| {
                            chrono::DateTime::parse_from_rfc2822(&h)
                                .map_err(|e| error!(e))
                                .map(|dt| orders.send_g_msg(GMsg::ServerDate(dt)))
                                .ok()
                        });
                }
            };
        }
        Msg::LoggedIn => {
            orders.skip();
            orders.send_msg(Msg::Fetch);
            orders.send_g_msg(GMsg::RouteChange(Route::Dashboard.into()));
        }

        Msg::Logout => {
            orders.perform_g_cmd(
                fetch_session()
                    .method(fetch::Method::Delete)
                    .fetch(|_| GMsg::AuthProxy(Box::new(Msg::LoggedIn))),
            );
        }
        Msg::Loop => {
            orders.skip();

            let (cancel, fut) = sleep_with_handle(Duration::from_secs(10), Msg::Fetch, Msg::Noop);

            model.cancel = Some(cancel);

            orders.perform_cmd(fut);
        }
        Msg::Noop => {}
    };
}

pub(crate) fn fetch_session() -> fetch::Request {
    fetch::Request::api_call(Session::endpoint_name()).with_auth()
}

/// Returns the CSRF token if one exists within the cookie.
pub(crate) fn csrf_token() -> Option<String> {
    let html_doc: HtmlDocument = HtmlDocument::from(JsValue::from(document()));
    let cookie = html_doc.cookie().unwrap();

    parse_cookie(&cookie)
}

/// Parses the CSRF token out of the cookie if one exists.
fn parse_cookie(cookie: &str) -> Option<String> {
    let re = Regex::new(r"csrftoken=([^;|$]+)").unwrap();

    let x = re.captures(cookie)?;

    x.get(1).map(|x| x.as_str().to_string())
}
