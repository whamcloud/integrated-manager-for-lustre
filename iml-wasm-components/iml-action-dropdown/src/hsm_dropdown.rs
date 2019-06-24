// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    action_dropdown::{self, action_dropdown, dropdown_header},
    dispatch_custom_event::dispatch_custom_event,
    hsm::{HsmControlParam, RecordAndHsmControlParam},
    model::{record_to_composite_id_string, LockType, Locks, Record},
};
use seed::{
    a, class,
    dom_types::{At, El, MessageMapper as _, UpdateEl},
    events::{mouse_ev, Ev},
    li,
    prelude::{wasm_bindgen, Orders},
};
use std::{collections::HashMap, iter};
use wasm_bindgen::JsValue;
use web_sys::Element;

#[derive(serde::Deserialize, serde::Serialize, Debug, Clone)]
pub struct HsmData {
    pub record: Record,
    pub locks: Locks,
    pub tooltip_placement: Option<iml_tooltip::TooltipPlacement>,
    pub tooltip_size: Option<iml_tooltip::TooltipSize>,
}

pub struct Model {
    pub record: Record,
    pub locks: Locks,
    pub open: bool,
    pub tooltip: iml_tooltip::Model,
    pub destroyed: bool,
}

#[derive(Clone)]
pub enum Msg {
    ActionDropdown(action_dropdown::Msg),
    SetLocks(Locks),
    SetRecord(Record),
    Destroy,
}

/// The sole source of updating the model
pub fn update(msg: Msg, model: &mut Model, _orders: &mut Orders<Msg>) {
    if model.destroyed {
        return;
    }

    match msg {
        Msg::ActionDropdown(msg) => match msg {
            action_dropdown::Msg::Open(open) => {
                model.open = open;
            }
        },
        Msg::SetRecord(record) => {
            model.record = record;
        }
        Msg::SetLocks(locks) => {
            model.locks = locks;
        }
        Msg::Destroy => {
            model.locks = HashMap::new();
            model.destroyed = true;
        }
    };
}

fn get_record_els_from_hsm_control_params(
    record: &Record,
    hsm_control_params: &[HsmControlParam],
    tooltip_config: &iml_tooltip::Model,
) -> Vec<El<action_dropdown::Msg>> {
    let ys = hsm_control_params.iter().map(|y| {
        let x = RecordAndHsmControlParam {
            record: record.clone(),
            hsm_control_param: y.clone(),
        };

        li![
            class!["tooltip-container", "tooltip-hover"],
            a![&y.verb],
            mouse_ev(Ev::Click, move |ev| {
                ev.stop_propagation();
                ev.prevent_default();

                dispatch_custom_event("hsm_action_selected", &x);

                action_dropdown::Msg::Open(false)
            }),
            iml_tooltip::tooltip(&y.long_description, tooltip_config)
        ]
    });

    iter::once(dropdown_header(&record.label))
        .chain(ys)
        .collect()
}

fn view(
    Model {
        record,
        open,
        locks,
        tooltip,
        destroyed,
    }: &Model,
) -> El<Msg> {
    if *destroyed {
        return seed::empty();
    }

    let hsm_control_params = match record.hsm_control_params {
        Some(ref x) if !x.is_empty() => x,
        _ => {
            return action_dropdown(action_dropdown::State::Empty).map_message(Msg::ActionDropdown)
        }
    };

    let id = record_to_composite_id_string(record.content_type_id, record.id);

    let has_locks = iter::once(locks.get(&id))
        .filter_map(std::convert::identity)
        .flatten()
        .any(|x| x.lock_type == LockType::Write);

    if has_locks {
        return action_dropdown(action_dropdown::State::Disabled).map_message(Msg::ActionDropdown);
    }

    let record_els = get_record_els_from_hsm_control_params(&record, &hsm_control_params, tooltip);

    action_dropdown(action_dropdown::State::Populated(*open, record_els))
        .map_message(Msg::ActionDropdown)
}

fn window_events(model: &Model) -> Vec<seed::events::Listener<Msg>> {
    if model.destroyed {
        return vec![];
    }

    vec![mouse_ev(Ev::Click, move |_| {
        Msg::ActionDropdown(action_dropdown::Msg::Open(false))
    })]
}

#[wasm_bindgen]
pub struct HsmCallbacks {
    app: seed::App<Msg, Model, El<Msg>>,
}

#[wasm_bindgen]
impl HsmCallbacks {
    pub fn destroy(&self) {
        self.app.update(Msg::Destroy);
    }
    pub fn set_locks(&self, locks: JsValue) {
        let locks: Locks = locks.into_serde().unwrap();
        self.app.update(Msg::SetLocks(locks));
    }
    pub fn set_hsm_record(&self, record: JsValue) {
        let record: Record = record.into_serde().unwrap();

        self.app.update(Msg::SetRecord(record));
    }
}

#[wasm_bindgen]
pub fn hsm_action_dropdown_component(x: &JsValue, el: Element) -> HsmCallbacks {
    log::info!("Incoming value is: {:?}", x);

    let HsmData {
        record,
        locks,
        tooltip_placement,
        tooltip_size,
    } = x.into_serde().expect("Could not parse incoming data");

    let model = Model {
        record,
        locks,
        tooltip: iml_tooltip::Model {
            placement: tooltip_placement.unwrap_or_default(),
            size: tooltip_size.unwrap_or_default(),
            ..Default::default()
        },
        destroyed: false,
        open: false,
    };

    let app = seed::App::build(model, update, view)
        .window_events(window_events)
        .mount(el)
        .finish()
        .run();

    HsmCallbacks { app: app.clone() }
}
