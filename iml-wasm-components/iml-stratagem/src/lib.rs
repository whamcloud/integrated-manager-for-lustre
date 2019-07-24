// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

mod add_stratagem_button;
mod inode_error;
pub mod inode_table;

use bootstrap_components::bs_well::well;
use seed::prelude::*;

use iml_duration_picker::{self, duration_picker};
use iml_grafana_chart::{grafana_chart, GRAFANA_DASHBOARD_ID, GRAFANA_DASHBOARD_NAME};
use iml_toggle::toggle;
use seed::{class, div, dom_types::At, h4, style};

/// Record from the `chroma_core_stratagemconfiguration` table
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct StratagemConfiguration {
    pub id: u32,
    pub filesystem_id: u32,
    pub interval: u64,
    pub report_duration: Option<u64>,
    pub purge_duration: Option<u64>,
    pub immutable_state: bool,
    pub state: String,
}

#[derive(Debug)]
pub struct Model {
    pub destroyed: bool,
    pub fs_id: u32,
    pub run_config: iml_duration_picker::Model,
    pub report_active: bool,
    pub report_config: iml_duration_picker::Model,
    pub purge_active: bool,
    pub purge_config: iml_duration_picker::Model,
    pub inode_table: inode_table::Model,
    pub add_stratagem_button: add_stratagem_button::Model,
    pub ready: bool,
    pub configured: bool,
}

#[derive(Debug, Clone)]
pub struct ReadyAndFs {
    pub ready: bool,
    pub fs_id: u32,
}

impl Default for Model {
    fn default() -> Self {
        Model {
            fs_id: 1,
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
            purge_active: false,
            inode_table: inode_table::Model::default(),
            destroyed: false,
            ready: false,
            configured: false,
            add_stratagem_button: add_stratagem_button::Model::default(),
        }
    }
}

// Update
#[derive(Clone, Debug)]
pub enum Msg {
    Destroy,
    TogglePurge(iml_toggle::Active),
    ToggleReport(iml_toggle::Active),
    RunConfig(iml_duration_picker::Msg),
    SetConfig(Option<StratagemConfiguration>),
    ReportConfig(iml_duration_picker::Msg),
    PurgeConfig(iml_duration_picker::Msg),
    InodeTable(inode_table::Msg),
    AddStratagemButton(add_stratagem_button::Msg),
    WindowClick,
}

pub fn update(msg: Msg, model: &mut Model, _orders: &mut Orders<Msg>) {
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
        }
        Msg::SetConfig(config) => match config {
            Some(c) => {
                model.configured = true;
                model.run_config.value = c.interval.to_string();
                model.report_active = c.report_duration.is_some();
                match c.report_duration {
                    None => {
                        model.report_config.value = "".to_string();
                        model.report_config.disabled = true;
                    }
                    Some(x) => model.report_config.value = x.to_string(),
                }

                model.purge_active = c.purge_duration.is_some();
                match c.purge_duration {
                    None => {
                        model.purge_config.value = "".to_string();
                        model.purge_config.disabled = true;
                    }
                    Some(x) => model.purge_config.value = x.to_string(),
                }
            }
            None => {
                model.configured = false;
                model.run_config.value = "".to_string();
                model.report_active = false;
                model.report_config.value = "".to_string();
                model.report_config.disabled = true;
                model.purge_active = false;
                model.purge_config.value = "".to_string();
                model.purge_config.disabled = true;
            }
        },
        Msg::InodeTable(msg) => {
            *_orders = call_update(inode_table::update, msg, &mut model.inode_table)
                .map_message(Msg::InodeTable);
        }
        Msg::AddStratagemButton(msg) => {
            model.add_stratagem_button.fs_id = model.fs_id;
            *_orders = call_update(
                add_stratagem_button::update,
                msg,
                &mut model.add_stratagem_button,
            )
            .map_message(Msg::AddStratagemButton);
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

fn detail_header<T>(header: &str) -> El<T> {
    h4![
        header,
        style! {
        "color" => "#777",
        "grid-column" => "1 / span 3",
        "grid-row-end" => "1"}
    ]
}

fn detail_panel<T>(children: Vec<El<T>>) -> El<T> {
    well(children)
        .add_style("display".into(), "grid".into())
        .add_style("grid-template-columns".into(), "50% 25% 25%".into())
        .add_style("grid-row-gap".into(), px(20))
}

fn detail_label<T>(content: &str) -> El<T> {
    div![
        content,
        style! { "font-weight" => "700", "color" => "#777" }
    ]
}

// View
pub fn view(model: &Model) -> El<Msg> {
    let mut configuration_component = vec![
        detail_header("Stratagem Configuration"),
        detail_label("Scan filesystem every"),
        div![
            class!["input-group"],
            duration_picker(&model.run_config).map_message(Msg::RunConfig)
        ],
        div![],
        detail_label("Generate report on files older than"),
        div![
            class!["input-group"],
            duration_picker(&model.report_config).map_message(Msg::ReportConfig)
        ],
        toggle(!model.report_config.disabled).map_message(Msg::ToggleReport),
        detail_label("Purge Files older than"),
        div![
            class!["input-group"],
            duration_picker(&model.purge_config).map_message(Msg::PurgeConfig)
        ],
        toggle(!model.purge_config.disabled).map_message(Msg::TogglePurge),
    ];

    if model.configured {
        div![
            h4![class!["section-header"], "Stratagem"],
            well(vec![grafana_chart(
                GRAFANA_DASHBOARD_ID,
                GRAFANA_DASHBOARD_NAME,
                "10s",
                2,
                "100%",
                "600"
            )]),
            inode_table::view(&model.inode_table).map_message(Msg::InodeTable),
            detail_panel(configuration_component)
        ]
    } else {
        configuration_component.extend(vec![add_stratagem_button::view(
            &model.add_stratagem_button,
        )
        .map_message(Msg::AddStratagemButton)]);

        div![
            h4![class!["section-header"], "Stratagem"],
            detail_panel(configuration_component)
        ]
    }
}

fn window_events(model: &Model) -> Vec<seed::events::Listener<Msg>> {
    if model.destroyed {
        return vec![];
    }

    vec![simple_ev(Ev::Click, Msg::WindowClick)]
}
