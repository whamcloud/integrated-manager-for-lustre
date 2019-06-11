// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

mod action_dropdown_error;
mod action_items;
mod api_transforms;
mod button;
mod dispatch_custom_event;
mod fetch_actions;
mod hsm;
mod model;
mod update;

use crate::{
    action_items::get_record_els,
    api_transforms::{lock_list, record_to_composite_id_string},
    hsm::contains_hsm_params,
    model::{Data, Locks, Model, Record, RecordMap, Records},
    update::{update, Msg},
};
use cfg_if::cfg_if;
use seed::{
    class, div,
    dom_types::{mouse_ev, At, El, Ev, UpdateEl},
    prelude::wasm_bindgen,
    ul,
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
fn open_class(open: &bool) -> &str {
    if *open {
        "open"
    } else {
        ""
    }
}

/// The top-level component we pass to the virtual dom.
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
        ..
    }: &Model,
) -> Vec<El<Msg>> {
    if *destroyed {
        return vec![seed::empty()];
    }

    let next_open = Msg::Open(!open);

    let has_locks = lock_list(&locks, &records).next().is_some();

    let record_els = get_record_els(available_actions, records, flag, tooltip);

    let open_class = open_class(open);

    let has_hsm_params = contains_hsm_params(&records);

    let mut btn = button::get_button(
        has_locks,
        !button_activated || !available_actions.is_empty() || has_hsm_params,
        *first_fetch_active,
        next_open,
    );

    if !has_hsm_params && !records.is_empty() && !button_activated {
        btn.listeners.push(mouse_ev(Ev::MouseMove, move |ev| {
            ev.stop_propagation();
            ev.prevent_default();

            Msg::StartFetch
        }));
    }

    vec![div![
        class!["action-dropdown"],
        div![
            class!["btn-group dropdown", &open_class],
            btn,
            ul![class!["dropdown-menu", &open_class], record_els],
        ]
    ]]
}

fn window_events(_model: &Model) -> Vec<seed::dom_types::Listener<Msg>> {
    vec![mouse_ev(Ev::Click, move |_ev| Msg::Open(false))]
}

#[wasm_bindgen]
pub struct Callbacks {
    app: seed::App<Msg, Model, Vec<El<Msg>>>,
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
    pub fn set_records(&self, records: JsValue) {
        let records: Vec<Record> = records.into_serde().unwrap();
        let records = records_to_map(records);

        self.app.update(Msg::SetRecords(records));
        self.app.update(Msg::StartFetch);
    }
    pub fn set_hsm_records(&self, records: JsValue) {
        let records: Vec<Record> = records.into_serde().unwrap();
        let records = records_to_map(records);

        self.app.update(Msg::UpdateHsmRecords(records));
    }
}

fn records_to_map(xs: Records) -> RecordMap {
    xs.into_iter()
        .map(|r| {
            let id = record_to_composite_id_string(r.content_type_id, r.id);

            (id, r)
        })
        .collect()
}

#[wasm_bindgen]
pub fn action_dropdown(x: &JsValue, el: Element) -> Callbacks {
    init_log();

    log::info!("Incoming value is: {:?}", x);

    let Data {
        records,
        locks,
        flag,
        tooltip_placement,
        tooltip_size,
    } = x.into_serde().expect("Could not parse incoming data");

    let records: RecordMap = records_to_map(records);
    let has_hsm_params = contains_hsm_params(&records);
    let model = Model {
        records,
        locks,
        flag,
        tooltip: iml_tooltip::Model {
            placement: tooltip_placement.unwrap_or_default(),
            size: tooltip_size.unwrap_or_default(),
            ..Default::default()
        },
        ..Default::default()
    };

    let app = seed::App::build(model, update, view)
        .window_events(window_events)
        .mount(el)
        .finish()
        .run();

    // if !has_hsm_params {
    //     spawn_local(fetch_actions::get_actions(app.clone()));
    // }

    Callbacks { app: app.clone() }
}
