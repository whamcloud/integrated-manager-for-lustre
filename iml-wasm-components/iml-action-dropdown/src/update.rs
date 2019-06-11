// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    action_dropdown_error::ActionDropdownError,
    fetch_actions, model,
    model::{group_actions_by_label, sort_actions},
};
use futures::Future;
use seed::prelude::Orders;
use std::collections::HashMap;

#[derive(Clone)]
pub enum Msg {
    Open(bool),
    StartFetch,
    FetchActions,
    ActionsFetched(seed::fetch::FetchObject<model::AvailableActionsApiData>),
    UpdateHsmRecords(model::RecordMap),
    SetRecords(model::RecordMap),
    SetLocks(model::Locks),
    Destroy,
    Error(ActionDropdownError),
    Noop,
}

/// The sole source of updating the model
pub fn update(msg: Msg, model: &mut model::Model, orders: &mut Orders<Msg>) {
    match msg {
        Msg::Noop => {}
        Msg::Error(e) => log::error!("An error has occurred {}", e),
        Msg::Open(open) => {
            model.open = open;
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
                    let model::AvailableActionsApiData { objects, .. } = resp.data;

                    model.available_actions = group_actions_by_label(objects, &model.records)
                        .into_iter()
                        .map(|(k, xs)| (k, sort_actions(xs)))
                        .collect();
                }
                Err(fail_reason) => {
                    log::error!("Fetch failed: {:?}", fail_reason);
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
        Msg::SetRecords(records) => {
            model.records = records;
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
            // model.records = model
            //     .records
            //     .drain()
            //     .filter(|(_, x)| x.hsm_control_params.is_some())
            //     .chain(action_records)
            //     .collect();
            model.button_activated = true;
            model.first_fetch_active = true;

            orders.send_msg(Msg::FetchActions);
        }
    };
}
