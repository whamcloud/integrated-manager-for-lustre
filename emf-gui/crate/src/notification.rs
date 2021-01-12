// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{components::ActivityHealth, GMsg};
use futures::FutureExt;
use seed::prelude::Orders;
use wasm_bindgen::JsValue;
use wasm_bindgen_futures::JsFuture;
use web_sys::{Notification as N, NotificationOptions as NO, NotificationPermission as NP, ServiceWorkerRegistration};

#[derive(Default)]
pub(crate) struct Model {
    svc: Option<ServiceWorkerRegistration>,
}

#[derive(Clone, Debug)]
pub enum Msg {
    Close,
    Display(String, String),
    Error(String),
    Nothing,
    SetSVCWorker(JsValue),
    Update(String, String),
}

pub(crate) fn update(u: Msg, m: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match u {
        Msg::Close => {
            if let Some(svc) = &m.svc {
                let ns_p = svc.get_notifications().unwrap();
                orders.perform_cmd(close(ns_p));
            }
        }
        Msg::Display(title, body) => {
            let mut opts = NO::new();
            opts.tag("emf-alert")
                .icon("/favicon.ico")
                .require_interaction(true)
                .body(body.as_str());

            if let Some(svc) = &m.svc {
                let promise = svc.show_notification_with_options(title.as_str(), &opts).unwrap();
                orders.perform_cmd(JsFuture::from(promise).map(|_| Ok(Msg::Nothing)));
            } else {
                let n = N::new_with_options(title.as_str(), &opts).unwrap();
                seed::set_timeout(Box::new(move || n.close()), 9000);
            }
        }
        Msg::Error(s) => seed::log!(s),
        Msg::Nothing => {}
        Msg::SetSVCWorker(js) => m.svc = Some(ServiceWorkerRegistration::from(js)),
        Msg::Update(title, body) => {
            if let Some(svc) = &m.svc {
                let ns_p = svc.get_notifications().unwrap();
                orders.perform_cmd(refresh(ns_p, title, body));
            }
        }
    }
}

pub(crate) async fn init() -> Result<Msg, Msg> {
    if N::permission() == NP::Default {
        let rq_p = N::request_permission().unwrap();
        JsFuture::from(rq_p).await.unwrap();
    }

    if N::permission() == NP::Granted {
        let svc_p = seed::window()
            .navigator()
            .service_worker()
            .register("static/notification.sw.js");

        JsFuture::from(svc_p).await.map(Msg::SetSVCWorker).map_err(|v| {
            Msg::Error(
                v.as_string()
                    .unwrap_or_else(|| "failed to register service worker".to_string()),
            )
        })
    } else {
        Err(Msg::Error("notifications not permitted".to_string()))
    }
}

pub(crate) fn generate(amsg: Option<String>, old: &ActivityHealth, new: &ActivityHealth) -> Msg {
    if new == old {
        Msg::Nothing
    } else if new.count == 0 {
        Msg::Close
    } else {
        let title;
        let body;
        if let Some(msg) = amsg {
            title = msg;
            if old.count > new.count {
                if new.count > 1 {
                    body = format!("{} alerts remain", new.count);
                } else {
                    body = String::from("1 alert remains");
                }
            } else if new.count > 2 {
                body = format!("+{} more alerts", new.count - 1);
            } else if new.count == 2 {
                body = String::from("+1 more alert");
            } else {
                body = String::new();
            }
        } else {
            if new.count > 1 {
                title = format!("{} alerts", new.count);
            } else {
                title = String::from("1 alert");
            }
            body = String::new();
        }

        if old < new {
            Msg::Display(title, body)
        } else {
            Msg::Update(title, body)
        }
    }
}

async fn refresh(ns_p: js_sys::Promise, title: String, body: String) -> Result<Msg, Msg> {
    let v = JsFuture::from(ns_p).await.unwrap();
    let len = js_sys::Array::from(&v).length();
    if len > 0 {
        Ok(Msg::Display(title, body))
    } else {
        Ok(Msg::Nothing)
    }
}

async fn close(ns_p: js_sys::Promise) -> Result<Msg, Msg> {
    let v = JsFuture::from(ns_p).await.unwrap();
    let mut ns = js_sys::Array::from(&v).to_vec();
    while let Some(v) = ns.pop() {
        N::from(v).close();
    }
    Ok(Msg::Nothing)
}
