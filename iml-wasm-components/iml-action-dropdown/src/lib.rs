// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

mod action_dropdown;
mod action_dropdown_error;
mod action_items;
mod dispatch_custom_event;
mod fetch;
mod hsm;
pub mod hsm_dropdown;
mod model;
mod update;

use crate::{
    action_dropdown::action_dropdown,
    action_items::get_record_els,
    model::{lock_list, records_to_map, Data, Locks, Model, Record, RecordMap},
    update::{update, Msg},
};
use cfg_if::cfg_if;
use seed::{
    events::{mouse_ev, Ev},
    dom_types::{El, MessageMapper as _},
    prelude::wasm_bindgen,
};
use wasm_bindgen::JsValue;
use web_sys::Element;

cfg_if! {
    if #[cfg(feature = "console_log")] {
        fn init_log() {
            use log::Level;

            if let Err(e) = console_log::init_with_level(Level::Trace) {
                log::info!("Error initializing logger (it may have already been initialized): {:?}", e)
            }
        }
    } else {
        fn init_log() {}
    }
}

// View
fn view(
    Model {
        records,
        open,
        locks,
        available_actions,
        button_activated,
        first_fetch_active,
        flag,
        tooltip,
        destroyed,
        urls,
        ..
    }: &Model,
) -> El<Msg> {
    if *destroyed {
        return seed::empty();
    }

    let has_locks = lock_list(&locks, &records).next().is_some();

    let record_els = get_record_els(available_actions, records, flag, tooltip);

    if *first_fetch_active {
        return action_dropdown(action_dropdown::State::Waiting).map_message(Msg::ActionDropdown);
    }

    if has_locks {
        return action_dropdown(action_dropdown::State::Disabled).map_message(Msg::ActionDropdown);
    }

    if *button_activated && available_actions.is_empty() {
        return action_dropdown(action_dropdown::State::Empty).map_message(Msg::ActionDropdown);
    }

    let mut el = action_dropdown(action_dropdown::State::Populated(*open, record_els))
        .map_message(Msg::ActionDropdown);

    if (!records.is_empty() || urls.is_some()) && !button_activated {
        el.listeners.push(mouse_ev(Ev::MouseMove, move |ev| {
            ev.stop_propagation();
            ev.prevent_default();

            Msg::StartFetch
        }));
    }

    el
}

fn window_events(model: &Model) -> Vec<seed::events::Listener<Msg>> {
    if model.destroyed {
        return vec![];
    }

    vec![mouse_ev(Ev::Click, move |_ev| {
        Msg::ActionDropdown(action_dropdown::Msg::Open(false))
    })]
}

#[wasm_bindgen]
pub struct Callbacks {
    app: seed::App<Msg, Model, El<Msg>>,
}

#[wasm_bindgen]
impl Callbacks {
    pub fn destroy(&self) {
        self.app.update(Msg::Destroy);
    }
    pub fn set_locks(&self, locks: JsValue) {
        let locks: Locks = locks.into_serde().unwrap();
        self.app.update(Msg::SetLocks(locks));
    }
}

#[wasm_bindgen]
pub fn action_dropdown_component(x: &JsValue, el: Element) -> Callbacks {
    init_log();

    log::info!("Incoming value is: {:?}", x);

    let Data {
        records,
        locks,
        flag,
        tooltip_placement,
        tooltip_size,
        urls,
    } = x.into_serde().expect("Could not parse incoming data");

    let records: RecordMap = records_to_map(records);

    let model = Model {
        records,
        locks,
        flag,
        tooltip: iml_tooltip::Model {
            placement: tooltip_placement.unwrap_or_default(),
            size: tooltip_size.unwrap_or_default(),
            ..Default::default()
        },
        urls,
        ..Default::default()
    };

    let app = seed::App::build(model, update, view)
        .window_events(window_events)
        .mount(el)
        .finish()
        .run();

    Callbacks { app: app.clone() }
}
