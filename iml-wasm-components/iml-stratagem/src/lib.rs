// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

mod inode_error;
mod inode_table;

use iml_grafana_chart::grafana_chart;
use seed::prelude::*;

static DASHBOARD_ID: &str = "OBdCS5IWz";
static DASHBOARD_NAME: &str = "stratagem";

pub fn size_distribution_chart<T>() -> El<T> {
    grafana_chart(DASHBOARD_ID, DASHBOARD_NAME, "10s", 2, "100%", "600")
}

use cfg_if::cfg_if;
use iml_duration_picker::{self, duration_picker};
use iml_toggle::toggle;
use seed::{
    class, div, dom_types::MessageMapper as _, h4, prelude::*, style, table, tbody, td, th, thead,
    tr,
};
use web_sys::Element;

cfg_if! {
    if #[cfg(feature = "console_log")] {
        fn init_log() {
            use log::Level;
            match console_log::init_with_level(Level::Trace) {
                Ok(_) => (),
                Err(e) => log::info!("{:?}", e)
            };
        }
    } else {
        fn init_log() {}
    }
}

#[derive(Debug)]
struct Model {
    pub destroyed: bool,
    pub run_config: iml_duration_picker::Model,
    pub report_active: bool,
    pub report_config: iml_duration_picker::Model,
    pub purge_config: iml_duration_picker::Model,
    pub inode_table: inode_table::Model
}

impl Default for Model {
    fn default() -> Self {
        Model {
            run_config: iml_duration_picker::Model {
                value: "30".into(),
                exclude_units: vec![
                    iml_duration_picker::Unit::Minutes,
                    iml_duration_picker::Unit::Seconds,
                ],
                ..Default::default()
            },
            report_active: true,
            report_config: iml_duration_picker::Model {
                value: "30".into(),
                exclude_units: vec![
                    iml_duration_picker::Unit::Minutes,
                    iml_duration_picker::Unit::Seconds,
                ],
                ..Default::default()
            },
            purge_config: iml_duration_picker::Model {
                value: "30".into(),
                exclude_units: vec![
                    iml_duration_picker::Unit::Minutes,
                    iml_duration_picker::Unit::Seconds,
                ],
                ..Default::default()
            },
            inode_table: inode_table::Model::default(),
            destroyed: false,
        }
    }
}

// Update

#[derive(Clone, Debug)]
enum Msg {
    Destroy,
    TogglePurge(iml_toggle::Active),
    ToggleReport(iml_toggle::Active),
    RunConfig(iml_duration_picker::Msg),
    ReportConfig(iml_duration_picker::Msg),
    PurgeConfig(iml_duration_picker::Msg),
    InodeTable(inode_table::Msg),
    WindowClick,
}

fn update(msg: Msg, model: &mut Model, _orders: &mut Orders<Msg>) {
    log::trace!("Msg: {:#?}", msg);

    match msg {
        Msg::Destroy => model.destroyed = true,
        Msg::RunConfig(msg) => iml_duration_picker::update(msg, &mut model.run_config),
        Msg::ReportConfig(msg) => iml_duration_picker::update(msg, &mut model.report_config),
        Msg::PurgeConfig(msg) => iml_duration_picker::update(msg, &mut model.purge_config),
        Msg::ToggleReport(iml_toggle::Active(active)) => {
            model.report_config.disabled = !active;
        }
        Msg::TogglePurge(iml_toggle::Active(active)) => {
            model.purge_config.disabled = !active;
        },
        Msg::InodeTable(msg) => {
            *_orders = call_update(inode_table::update, msg, &mut model.inode_table).map_message(Msg::InodeTable);
        }
        Msg::WindowClick => {
            if model.run_config.watching.should_update() {
                model.run_config.watching.update();
            }

            if model.report_config.watching.should_update() {
                model.report_config.watching.update();
            }

            if model.purge_config.watching.should_update() {
                model.purge_config.watching.update();
            }
        }
    }

    log::trace!("Model: {:#?}", model);
}

// View
fn view(model: &Model) -> El<Msg> {
    let style_override =
        style! { "display" => "flex", "align-items" => "center", "line-height" => "unset" };

    div![
        class!["container", "container-full"],
        h4![class!["section-header"], "Top inode Users"],
        inode_table::view(&model.inode_table).map_message(Msg::InodeTable),
        div![
            class!["detail-panel"],
            h4![class!["section-header"], "Stratagem Configuration"],
            div![
                class!["detail-row"],
                div![style_override.clone(), "Scan filesystem every"],
                div![
                    style_override.clone(),
                    div![
                        class!["input-group"],
                        duration_picker(&model.run_config).map_message(Msg::RunConfig)
                    ]
                ]
            ],
            div![
                class!["detail-row"],
                div![
                    style_override.clone(),
                    "Generate report on files older than"
                ],
                div![
                    style_override.clone(),
                    div![
                        class!["input-group"],
                        duration_picker(&model.report_config).map_message(Msg::ReportConfig)
                    ],
                    toggle(!model.report_config.disabled).map_message(Msg::ToggleReport),
                ],
            ],
            div![
                class!["detail-row"],
                div![style_override.clone(), "Purge Files older than"],
                div![
                    style_override,
                    div![
                        class!["input-group"],
                        duration_picker(&model.purge_config).map_message(Msg::PurgeConfig)
                    ],
                    toggle(!model.purge_config.disabled).map_message(Msg::TogglePurge)
                ]
            ]
        ]
    ]
}

fn window_events(model: &Model) -> Vec<seed::events::Listener<Msg>> {
    if model.destroyed {
        return vec![];
    }

    vec![simple_ev(Ev::Click, Msg::WindowClick)]
}

#[wasm_bindgen]
pub struct StratagemCallbacks {
    app: seed::App<Msg, Model, El<Msg>>,
}

#[wasm_bindgen]
impl StratagemCallbacks {
    pub fn destroy(&self) {
        self.app.update(Msg::Destroy);
    }
}

#[wasm_bindgen]
pub fn render(el: Element) -> StratagemCallbacks {
    init_log();

    let app = seed::App::build(Model::default(), update, view)
        .mount(el)
        .window_events(window_events)
        .finish()
        .run();

    app.update(Msg::InodeTable(inode_table::Msg::FetchInodes));

    StratagemCallbacks { app: app.clone() }
}
