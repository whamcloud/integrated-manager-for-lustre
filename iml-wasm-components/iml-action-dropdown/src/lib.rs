// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

mod action_items;
mod api_transforms;
mod button;
mod dispatch_custom_event;
mod fetch_actions;
mod hsm;

use action_items::get_record_els;
use api_transforms::{
    group_actions_by_label, lock_list, record_to_composite_id_string, sort_actions,
};
use cfg_if::cfg_if;
use futures::Future;
use hsm::{contains_hsm_params, HsmControlParam};
use seed::{
    class, div,
    dom_types::{mouse_ev, At, El, Ev, UpdateEl},
    prelude::{wasm_bindgen, Orders},
    ul,
};
use std::collections::{HashMap, HashSet};
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

/// A record
#[derive(serde::Deserialize, serde::Serialize, Debug, PartialEq, Clone)]
pub struct Record {
    content_type_id: i64,
    id: i64,
    label: String,
    hsm_control_params: Option<Vec<HsmControlParam>>,
    #[serde(flatten)]
    extra: Option<HashMap<String, serde_json::Value>>,
}

/// A record map is a map of composite id's to labels
pub type RecordMap = HashMap<String, Record>;

/// Records is a vector of Record items
pub type Records = Vec<Record>;

/// Data is what is being passed into the component.
#[derive(serde::Deserialize, serde::Serialize, Debug, PartialEq, Clone)]
pub struct Data {
    records: Records,
    locks: Locks,
    flag: Option<String>,
    tooltip_placement: Option<iml_tooltip::TooltipPlacement>,
    tooltip_size: Option<iml_tooltip::TooltipSize>,
}

/// Metadata is the metadata object returned by a fetch call
#[derive(serde::Deserialize, serde::Serialize, Clone, Debug)]
pub struct MetaData {
    limit: u32,
    next: Option<u32>,
    offset: u32,
    previous: Option<u32>,
    total_count: u32,
}

/// AvailableActionsApiData contains the metadata and the `Vec` of objects returned by a fetch call
#[derive(serde::Deserialize, serde::Serialize, Clone, Debug)]
pub struct AvailableActionsApiData {
    meta: MetaData,
    objects: Vec<AvailableAction>,
}

/// ActionArgs contains the arguments to an action. It is currently not being used.
#[derive(serde::Deserialize, serde::Serialize, Clone, Debug, PartialEq, Eq)]
pub struct ActionArgs {
    host_id: Option<u64>,
    target_id: Option<u64>,
}

/// AvailableAction represents an action that will be displayed on the dropdown.
#[derive(serde::Deserialize, serde::Serialize, Clone, Debug, PartialEq, Eq)]
pub struct AvailableAction {
    args: Option<ActionArgs>,
    composite_id: String,
    class_name: Option<String>,
    confirmation: Option<String>,
    display_group: u64,
    display_order: u64,
    long_description: String,
    state: Option<String>,
    verb: String,
}

/// Combines the AvailableAction and Label
#[derive(serde::Deserialize, serde::Serialize, Clone, Debug)]
pub struct AvailableActionAndRecord {
    available_action: AvailableAction,
    record: Record,
    flag: Option<String>,
}

/// The ActionMap is a map consisting of actions grouped by the composite_id
pub type ActionMap = HashMap<String, Vec<AvailableAction>>;

/// Locks is a map of locks in which the key is a composite id string in the form `composite_id:id`
pub type Locks = HashMap<String, HashSet<LockChange>>;

/// The type of lock
#[derive(serde::Deserialize, serde::Serialize, Debug, Eq, PartialEq, Hash, Clone)]
#[serde(rename_all = "lowercase")]
pub enum LockType {
    Read,
    Write,
}

/// The Action associated with a `LockChange`
#[derive(serde::Deserialize, serde::Serialize, Debug, Eq, PartialEq, Hash, Clone)]
#[serde(rename_all = "lowercase")]
pub enum LockAction {
    Add,
    Remove,
}

/// A change to be applied to `Locks`
#[derive(serde::Deserialize, serde::Serialize, Debug, Eq, PartialEq, Hash, Clone)]
pub struct LockChange {
    pub job_id: u64,
    pub content_type_id: u64,
    pub item_id: u64,
    pub description: String,
    pub lock_type: LockType,
    pub action: LockAction,
}

// Model
#[derive(Default)]
pub struct Model {
    records: RecordMap,
    available_actions: ActionMap,
    request_controller: Option<seed::fetch::RequestController>,
    cancel: Option<futures::sync::oneshot::Sender<()>>,
    locks: Locks,
    open: bool,
    button_activated: bool,
    first_fetch_active: bool,
    flag: Option<String>,
    tooltip: iml_tooltip::Model,
    destroyed: bool,
}

#[derive(Debug, Clone)]
pub enum ActionDropdownError {
    Cancelled(futures::sync::oneshot::Canceled),
}

impl std::fmt::Display for ActionDropdownError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match *self {
            ActionDropdownError::Cancelled(ref err) => write!(f, "{}", err),
        }
    }
}

impl std::error::Error for ActionDropdownError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match *self {
            ActionDropdownError::Cancelled(ref err) => Some(err),
        }
    }
}

impl From<futures::sync::oneshot::Canceled> for ActionDropdownError {
    fn from(err: futures::sync::oneshot::Canceled) -> Self {
        ActionDropdownError::Cancelled(err)
    }
}

// Update
#[derive(Clone)]
pub enum Msg {
    Open(bool),
    StartFetch,
    FetchActions,
    ActionsFetched(seed::fetch::FetchObject<AvailableActionsApiData>),
    UpdateHsmRecords(RecordMap),
    SetRecords(RecordMap),
    SetLocks(Locks),
    Destroy,
    Error(ActionDropdownError),
    Noop,
}

/// The sole source of updating the model
fn update(msg: Msg, model: &mut Model, orders: &mut Orders<Msg>) {
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
                    let AvailableActionsApiData { objects, .. } = resp.data;

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
