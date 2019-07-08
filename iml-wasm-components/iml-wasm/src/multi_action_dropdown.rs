// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_action_dropdown::{deferred_action_dropdown as dad, has_locks, multi_dropdown};
use iml_utils::Locks;
use seed::{
    events::{mouse_ev, Ev},
    prelude::*,
};
use std::collections::HashMap;
use wasm_bindgen::JsValue;
use web_sys::Element;

fn window_events(model: &Model) -> Vec<seed::events::Listener<Msg>> {
    if model.destroyed || !model.multi_dropdown.dropdown.watching.should_update() {
        return vec![];
    }

    let id = model.multi_dropdown.id;

    vec![mouse_ev(Ev::Click, move |_| {
        Msg::DeferredActionDropdown(multi_dropdown::Msg::DeferredActionDropdown(dad::IdMsg(
            id,
            dad::Msg::WatchChange,
        )))
    })]
}

#[derive(Default)]
struct Model {
    multi_dropdown: multi_dropdown::Model,
    locks: Locks,
    destroyed: bool,
}

#[derive(Clone)]
enum Msg {
    SetLocks(Locks),
    DeferredActionDropdown(multi_dropdown::Msg),
    Destroy,
}

fn update(msg: Msg, model: &mut Model, orders: &mut Orders<Msg>) {
    if model.destroyed {
        return;
    }

    match msg {
        Msg::SetLocks(locks) => {
            model.locks = locks;

            model.multi_dropdown.dropdown.is_locked =
                has_locks(&model.locks, &model.multi_dropdown.records);
        }
        Msg::DeferredActionDropdown(msg) => {
            if let multi_dropdown::Msg::DeferredActionDropdown(dad::IdMsg(
                _,
                dad::Msg::FetchActions,
            )) = msg
            {
                model.multi_dropdown.dropdown.is_locked =
                    has_locks(&model.locks, &model.multi_dropdown.records);
            }

            *orders = call_update(multi_dropdown::update, msg, &mut model.multi_dropdown)
                .map_message(Msg::DeferredActionDropdown);
        }
        Msg::Destroy => {
            model.destroyed = true;
            model.locks = HashMap::new();

            *orders = call_update(
                multi_dropdown::update,
                multi_dropdown::Msg::DeferredActionDropdown(dad::IdMsg(
                    model.multi_dropdown.id,
                    dad::Msg::Destroy,
                )),
                &mut model.multi_dropdown,
            )
            .map_message(Msg::DeferredActionDropdown);
        }
    }
}

fn view(model: &Model) -> El<Msg> {
    multi_dropdown::view(&model.multi_dropdown).map_message(Msg::DeferredActionDropdown)
}

/// Data is what is being passed into the component.
#[derive(serde::Deserialize, serde::Serialize, Debug, Clone)]
pub struct Data {
    pub urls: Vec<String>,
    pub locks: Locks,
    pub flag: Option<String>,
    pub tooltip_placement: Option<iml_tooltip::TooltipPlacement>,
    pub tooltip_size: Option<iml_tooltip::TooltipSize>,
}

#[wasm_bindgen]
pub struct MadCallbacks {
    app: seed::App<Msg, Model, El<Msg>>,
}

#[wasm_bindgen]
impl MadCallbacks {
    pub fn destroy(&self) {
        self.app.update(Msg::Destroy);
    }
    pub fn set_locks(&self, locks: JsValue) {
        let locks: Locks = locks.into_serde().unwrap();
        self.app.update(Msg::SetLocks(locks));
    }
}

#[wasm_bindgen]
pub fn multi_action_dropdown_component(x: &JsValue, el: Element) -> MadCallbacks {
    crate::init_log();

    log::trace!("Incoming value is: {:?}", x);

    let Data {
        urls,
        locks,
        flag,
        tooltip_placement,
        tooltip_size,
    } = x.into_serde().expect("Could not parse incoming data");

    let model = Model {
        destroyed: false,
        locks,
        multi_dropdown: multi_dropdown::Model {
            id: 1,
            urls,
            records: HashMap::new(),
            dropdown: dad::Model {
                flag,
                tooltip: iml_tooltip::Model {
                    placement: tooltip_placement.unwrap_or_default(),
                    size: tooltip_size.unwrap_or_default(),
                    ..iml_tooltip::Model::default()
                },
                is_locked: false,
                ..dad::Model::default()
            },
        },
    };

    let app = seed::App::build(model, update, view)
        .window_events(window_events)
        .mount(el)
        .finish()
        .run();

    MadCallbacks { app: app.clone() }
}
