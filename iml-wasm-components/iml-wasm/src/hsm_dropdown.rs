// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_action_dropdown::{
    has_lock,
    hsm_action_dropdown::{update, view, HsmData, Model, Msg},
    Record,
};
use iml_utils::Locks;
use seed::prelude::*;
use wasm_bindgen::JsValue;
use web_sys::Element;

fn window_events(model: &Model) -> Vec<seed::events::Listener<Msg>> {
    if model.destroyed || !model.watching.should_update() {
        return vec![];
    }

    vec![simple_ev(Ev::Click, Msg::WatchChange)]
}

#[wasm_bindgen]
pub struct HsmCallbacks {
    app: seed::App<Msg, Model, Node<Msg>>,
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
    crate::init_log();

    log::info!("Incoming value is: {:?}", x);

    let HsmData {
        record,
        locks,
        tooltip_placement,
        tooltip_size,
    } = x.into_serde().expect("Could not parse incoming data");

    let app = seed::App::build(
        move |_, _| Model {
            id: 1,
            is_locked: has_lock(&locks, &record),
            tooltip: iml_tooltip::Model {
                placement: tooltip_placement.unwrap_or_default(),
                size: tooltip_size.unwrap_or_default(),
                ..Default::default()
            },
            record,
            locks,
            destroyed: false,
            watching: Default::default(),
        },
        update,
        view,
    )
    .window_events(window_events)
    .mount(el)
    .finish()
    .run();

    HsmCallbacks { app: app.clone() }
}
