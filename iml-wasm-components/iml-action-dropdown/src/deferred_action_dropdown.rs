// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    action_dropdown::{action_dropdown, dropdown_header},
    action_dropdown_error::ActionDropdownError,
    model::{
        self, composite_ids_to_query_string, sort_actions, ActionMap, ActionRecord,
        AvailableActionAndRecord,
    },
};
use futures::Future;
use iml_utils::{WatchState, dispatch_custom_event::dispatch_custom_event};
use iml_wire_types::{AvailableAction, CompositeId};
use seed::{
    a, attrs, button, class, div,
    events::{simple_ev, Ev},
    fetch::FetchObject,
    i, li,
    prelude::*,
    span, Request,
};
use std::{collections::HashMap, iter};

#[derive(Default)]
pub struct Model {
    pub watching: WatchState,
    pub is_locked: bool,
    pub actions: Vec<AvailableAction>,
    pub composite_ids: Vec<CompositeId>,
    pub request_controller: Option<seed::fetch::RequestController>,
    pub cancel: Option<futures::sync::oneshot::Sender<()>>,
    pub activated: bool,
    pub first_fetch_activated: bool,
    pub tooltip: iml_tooltip::Model,
    pub flag: Option<String>,
    pub destroyed: bool,
}

impl Model {
    pub fn is_active(&self) -> bool {
        self.activated
    }
}

#[derive(Clone)]
pub enum Msg<T: ActionRecord> {
    ActionClicked(AvailableActionAndRecord<T>),
    StartFetch,
    FetchActions,
    WatchChange,
    ActionsFetched(FetchObject<model::AvailableActions>),
    Error(ActionDropdownError),
    Destroy,
    Noop,
}

#[derive(Clone)]
pub struct IdMsg<T: Clone + ActionRecord>(pub u32, pub Msg<T>);

pub fn update<T: ActionRecord + 'static>(
    msg: IdMsg<T>,
    model: &mut Model,
    orders: &mut Orders<IdMsg<T>>,
) {
    if model.destroyed {
        return;
    }

    let IdMsg(id, msg) = msg;

    match msg {
        Msg::Noop => {
            orders.skip();
        }
        Msg::Error(e) => {
            log::error!("An error has occurred {}", e);
            orders.skip();
        }
        Msg::WatchChange => model.watching.update(),
        Msg::FetchActions => {
            model.cancel = None;

            let (fut, request_controller) = fetch_actions(id, &model.composite_ids);

            model.request_controller = request_controller;

            orders.skip().perform_cmd(fut);
        }
        Msg::ActionsFetched(fetch_object) => {
            model.request_controller = None;
            model.first_fetch_activated = false;

            match fetch_object.response() {
                Ok(resp) => {
                    let model::AvailableActions { objects, .. } = resp.data;
                    model.actions = objects;
                }
                Err(fail_reason) => {
                    orders.send_msg(IdMsg(id, Msg::Error(fail_reason.into())));
                }
            }

            let sleep = iml_sleep::Sleep::new(10000)
                .map(move |_| IdMsg(id, Msg::FetchActions))
                .map_err(|_| unreachable!());

            let (p, c) = futures::sync::oneshot::channel::<()>();

            model.cancel = Some(p);

            // We depend on the producer being dropped to signal
            // completion of the loop
            let c = c.map(move |_| IdMsg(id, Msg::Noop)).map_err(move |_| {
                log::info!("action poll timeout dropped");

                IdMsg(id, Msg::Noop)
            });

            let fut = sleep
                .select2(c)
                .map(futures::future::Either::split)
                .map(|(x, _)| x)
                .map_err(futures::future::Either::split)
                .map_err(|(x, _)| x);

            orders.perform_cmd(fut);
        }
        Msg::Destroy => {
            model.cancel = None;

            if let Some(c) = model.request_controller.take() {
                c.abort();
            }

            model.destroyed = true;
            model.composite_ids = vec![];
            model.actions = vec![];
        }
        Msg::ActionClicked(available_action_and_record) => {
            dispatch_custom_event("action_selected", &available_action_and_record);
        }
        Msg::StartFetch => {
            if !model.composite_ids.is_empty() {
                model.activated = true;
                model.first_fetch_activated = true;

                orders.send_msg(IdMsg(id, Msg::FetchActions));
            }
        }
    };
}

/// Performs a fetch to get the current available actions based on given
/// composite ids.
pub fn fetch_actions<T: ActionRecord + 'static>(
    id: u32,
    records: &[CompositeId],
) -> (
    impl Future<Item = IdMsg<T>, Error = IdMsg<T>>,
    Option<seed::fetch::RequestController>,
) {
    let mut request_controller = None;

    let fut = Request::new(format!(
        "/api/action/?limit=0&{}",
        composite_ids_to_query_string(records)
    ))
    .controller(|controller| request_controller = Some(controller))
    .fetch_json(move |x| IdMsg(id, Msg::ActionsFetched(x)));

    (fut, request_controller)
}

pub fn get_record_els<'a, T: ActionRecord + 'static>(
    id: u32,
    actions: ActionMap<'a, T>,
    flag: &Option<String>,
    tooltip_config: &iml_tooltip::Model,
) -> Vec<El<IdMsg<T>>> {
    actions
        .into_iter()
        .filter(|(_, xs)| !xs.is_empty())
        .map(|(k, xs)| (k, sort_actions(xs)))
        .flat_map(|(label, xs)| {
            let ys = xs.into_iter().map(|(action, record)| {
                let available_action_and_record = AvailableActionAndRecord {
                    available_action: action.clone(),
                    record: record.clone(),
                    flag: flag.clone(),
                };

                li![
                    class!["tooltip-container", "tooltip-hover"],
                    a![action.verb],
                    mouse_ev(Ev::Click, move |_| {
                        IdMsg(id, Msg::ActionClicked(available_action_and_record.clone()))
                    }),
                    iml_tooltip::tooltip(&action.long_description, tooltip_config)
                ]
            });

            iter::once(dropdown_header(&label))
                .chain(ys)
                .chain(iter::once(li![class!["divider"]]))
        })
        .collect()
}

pub fn render<'a, T: 'static + ActionRecord>(
    id: u32,
    model: &Model,
    record: &'a T,
) -> El<IdMsg<T>> {
    let xs = model
        .actions
        .iter()
        .filter(|x| x.composite_id == record.composite_id().to_string())
        .map(|x| (x, record))
        .collect();

    let mut actions = HashMap::new();
    actions.insert(record.label().into(), xs);

    render_with_action(id, &model, actions)
}

// View
pub fn render_with_action<'a, T: 'static + ActionRecord>(
    id: u32,
    model: &Model,
    actions: ActionMap<'a, T>,
) -> El<IdMsg<T>> {
    if model.destroyed {
        seed::empty()
    } else if model.first_fetch_activated {
        div![
            class!["action-dropdown"],
            button![
                attrs! {At::Disabled => true},
                class!["btn", "btn-primary", "btn-sm"],
                "Waiting",
                i![class!["fa", "fa-spinner", "fa-fw", "fa-spin"]]
            ]
        ]
    } else if !model.activated {
        let mut d = action_dropdown(model.watching.is_open(), model.is_locked, vec![span![]]);

        d.listeners
            .push(simple_ev(Ev::MouseMove, IdMsg(id, Msg::StartFetch)));

        d
    } else {
        let record_els = get_record_els(id, actions, &model.flag, &model.tooltip);

        let mut el = action_dropdown(model.watching.is_open(), model.is_locked, record_els);

        el.listeners
            .push(simple_ev(Ev::Click, IdMsg(id, Msg::WatchChange)));

        el
    }
}
