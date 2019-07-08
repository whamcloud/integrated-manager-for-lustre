// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_action_dropdown::{deferred_action_dropdown as dad, has_lock, Locks, Record};
use iml_wire_types::ToCompositeId;
use seed::{
    events::{mouse_ev, Ev},
    prelude::*,
};
use std::collections::HashMap;
use wasm_bindgen::JsValue;
use web_sys::Element;

fn window_events(model: &Model) -> Vec<seed::events::Listener<Msg>> {
    if model.destroyed || !model.deferred_action_dropdown.watching.should_update() {
        return vec![];
    }

    let id = model.id;

    vec![mouse_ev(Ev::Click, move |_| {
        Msg::DeferredActionDropdown(dad::IdMsg(id, dad::Msg::WatchChange))
    })]
}

struct Model {
    id: u32,
    deferred_action_dropdown: dad::Model,
    locks: Locks,
    record: Record,
    destroyed: bool,
}

#[derive(Clone)]
enum Msg {
    SetLocks(Locks),
    DeferredActionDropdown(dad::IdMsg<Record>),
    Destroy,
}

fn update(msg: Msg, model: &mut Model, orders: &mut Orders<Msg>) {
    if model.destroyed {
        return;
    }

    match msg {
        Msg::SetLocks(locks) => {
            model.locks = locks;

            model.deferred_action_dropdown.is_locked = has_lock(&model.locks, &model.record);
        }
        Msg::DeferredActionDropdown(msg) => {
            *orders = call_update(dad::update, msg, &mut model.deferred_action_dropdown)
                .map_message(Msg::DeferredActionDropdown);
        }
        Msg::Destroy => {
            model.destroyed = true;
            model.locks = HashMap::new();

            *orders = call_update(
                dad::update,
                dad::IdMsg(model.id, dad::Msg::Destroy),
                &mut model.deferred_action_dropdown,
            )
            .map_message(Msg::DeferredActionDropdown);
        }
    }
}

fn view(model: &Model) -> El<Msg> {
    dad::render(model.id, &model.deferred_action_dropdown, &model.record)
        .map_message(Msg::DeferredActionDropdown)
}

/// Data is what is being passed into the component.
#[derive(serde::Deserialize, serde::Serialize, Debug, Clone)]
pub struct Data {
    pub record: Record,
    pub locks: Locks,
    pub flag: Option<String>,
    pub tooltip_placement: Option<iml_tooltip::TooltipPlacement>,
    pub tooltip_size: Option<iml_tooltip::TooltipSize>,
}

#[wasm_bindgen]
pub struct DadCallbacks {
    app: seed::App<Msg, Model, El<Msg>>,
}

#[wasm_bindgen]
impl DadCallbacks {
    pub fn destroy(&self) {
        self.app.update(Msg::Destroy);
    }
    pub fn set_locks(&self, locks: JsValue) {
        let locks: Locks = locks.into_serde().unwrap();
        self.app.update(Msg::SetLocks(locks));
    }
}

#[wasm_bindgen]
pub fn deferred_action_dropdown_component(x: &JsValue, el: Element) -> DadCallbacks {
    crate::init_log();

    log::trace!("Incoming value is: {:?}", x);

    let Data {
        record,
        locks,
        flag,
        tooltip_placement,
        tooltip_size,
    } = x.into_serde().expect("Could not parse incoming data");

    let model = Model {
        id: record.id,
        destroyed: false,
        deferred_action_dropdown: dad::Model {
            flag,
            composite_ids: vec![record.composite_id()],
            tooltip: iml_tooltip::Model {
                placement: tooltip_placement.unwrap_or_default(),
                size: tooltip_size.unwrap_or_default(),
                ..iml_tooltip::Model::default()
            },
            is_locked: has_lock(&locks, &record),
            ..dad::Model::default()
        },
        record,
        locks,
    };

    let app = seed::App::build(model, update, view)
        .window_events(window_events)
        .mount(el)
        .finish()
        .run();

    DadCallbacks { app: app.clone() }
}
