use crate::{sleep_with_handle, FailReasonExt, GMsg, RequestExt, Route, SessionExt};
use futures::channel::oneshot;
use iml_wire_types::{EndpointName, Session};
use regex::Regex;
use seed::{browser::service::fetch, prelude::*, *};
use std::time::Duration;
use wasm_bindgen::JsValue;
use web_sys::HtmlDocument;

#[derive(Default)]
pub struct Model {
    session: Option<Session>,
    pub state: State,
    request_controller: Option<fetch::RequestController>,
    cancel: Option<oneshot::Sender<()>>,
}

impl Model {
    pub(crate) fn get_session(&self) -> Option<&Session> {
        self.session.as_ref()
    }
}

#[derive(PartialEq, Eq)]
pub enum State {
    Fetching,
    Stopped,
}

impl Default for State {
    fn default() -> Self {
        Self::Fetching
    }
}

#[allow(clippy::large_enum_variant)]
#[derive(Clone)]
pub enum Msg {
    Fetch,
    Fetched(fetch::ResponseDataResult<Session>),
    SetSession(Session),
    Loop,
    Stop,
    Noop,
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::Fetch => {
            model.state = State::Fetching;
            model.cancel = None;

            let request = fetch_session().controller(|controller| model.request_controller = Some(controller));

            orders.skip().perform_cmd(request.fetch_json_data(Msg::Fetched));
        }
        Msg::SetSession(session) => {
            if session.needs_login() {
                orders.send_g_msg(GMsg::RouteChange(Route::Login.into()));
            }

            model.session = Some(session);
        }
        Msg::Fetched(data_result) => {
            let next_session = match data_result {
                Ok(resp) => resp,
                Err(fail_reason) => {
                    log!(format!("Error during session poll: {}", fail_reason.message()));

                    orders.skip().send_msg(Msg::Loop);

                    return;
                }
            };

            if next_session.needs_login() {
                orders.send_g_msg(GMsg::RouteChange(Route::Login.into()));
            } else {
                orders.send_msg(Msg::Loop);
            }

            model.session = Some(next_session);
        }
        Msg::Loop => {
            orders.skip();

            if model.state == State::Stopped {
                return;
            }

            let (cancel, fut) = sleep_with_handle(Duration::from_secs(10), Msg::Fetch, Msg::Noop);

            model.cancel = Some(cancel);

            orders.perform_cmd(fut);
        }
        Msg::Stop => {
            model.state = State::Stopped;
            model.cancel = None;

            if let Some(c) = model.request_controller.take() {
                c.abort();
            }
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
