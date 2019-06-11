// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    action_dropdown_error::ActionDropdownError,
    fetch_actions, model,
    model::{group_actions_by_label, record_to_map, sort_actions},
};
use futures::Future;
use seed::{fetch::FetchObject, prelude::Orders};
use std::collections::HashMap;

#[derive(Clone)]
pub enum Msg {
    Open(bool),
    StartFetch,
    FetchActions,
    FetchUrls,
    UrlsFetched(Vec<FetchObject<model::Record>>),
    ActionsFetched(FetchObject<model::AvailableActions>),
    UpdateHsmRecords(model::RecordMap),
    SetLocks(model::Locks),
    Destroy,
    Error(ActionDropdownError),
    Noop,
}

/// The sole source of updating the model
pub fn update(msg: Msg, model: &mut model::Model, orders: &mut Orders<Msg>) {
    if model.destroyed {
        return;
    }

    match msg {
        Msg::Noop => {
            orders.skip();
        }
        Msg::Error(e) => {
            log::error!("An error has occurred {}", e);
            orders.skip();
        }
        Msg::Open(open) => {
            model.open = open;
        }
        Msg::FetchUrls => {
            if let Some(urls) = model.urls.take() {
                orders.skip().perform_cmd(fetch_actions::fetch_urls(urls));
            }
        }
        Msg::UrlsFetched(xs) => {
            model.records = xs
                .into_iter()
                .filter_map(|x| match x.response() {
                    Ok(resp) => Some(resp.data),
                    Err(e) => {
                        orders.send_msg(Msg::Error(e.into()));

                        None
                    }
                })
                .map(record_to_map)
                .collect();

            orders.skip().send_msg(Msg::FetchActions);
        }
        Msg::FetchActions => {
            model.cancel = None;

            let (fut, request_controller) = fetch_actions::fetch_actions(&model.records);

            model.request_controller = request_controller;

            orders.skip().perform_cmd(fut);
        }
        Msg::ActionsFetched(fetch_object) => {
            model.request_controller = None;
            model.first_fetch_active = false;

            match fetch_object.response() {
                Ok(resp) => {
                    let model::AvailableActions { objects, .. } = resp.data;

                    model.available_actions = group_actions_by_label(objects, &model.records)
                        .into_iter()
                        .map(|(k, xs)| (k, sort_actions(xs)))
                        .collect();
                }
                Err(fail_reason) => {
                    orders.send_msg(Msg::Error(fail_reason.into()));
                }
            }

            let sleep = iml_sleep::Sleep::new(10000)
                .map(|_| Msg::FetchActions)
                .map_err(|_| unreachable!());

            let (p, c) = futures::sync::oneshot::channel::<()>();

            model.cancel = Some(p);

            let c = c
                .inspect(|_| log::info!("action poll timeout dropped"))
                .map(|_| Msg::Noop)
                .map_err(|e| Msg::Error(e.into()));

            let fut = sleep
                .select2(c)
                .map(futures::future::Either::split)
                .map(|(x, _)| x)
                .map_err(futures::future::Either::split)
                .map_err(|(x, _)| x);

            orders.perform_cmd(fut);
        }
        Msg::UpdateHsmRecords(hsm_records) => {
            model.records = model
                .records
                .drain()
                .filter(|(_, x)| x.hsm_control_params == None)
                .chain(hsm_records)
                .collect();

            model.button_activated = true;
        }
        Msg::SetLocks(locks) => {
            model.locks = locks;
        }
        Msg::Destroy => {
            if let Some(p) = model.cancel.take() {
                let _ = p.send(()).is_ok();
            };

            if let Some(c) = model.request_controller.take() {
                c.abort();
            }

            model.records = HashMap::new();
            model.available_actions = HashMap::new();
            model.locks = HashMap::new();
            model.destroyed = true;
        }
        Msg::StartFetch => {
            model.button_activated = true;
            model.first_fetch_active = true;

            let msg = if model.urls.is_some() {
                Msg::FetchUrls
            } else {
                Msg::FetchActions
            };

            orders.send_msg(msg);
        }
    };
}
