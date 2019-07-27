// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

mod delete_stratagem_button;
mod enable_stratagem_button;
mod inode_error;
pub mod inode_table;
mod update_stratagem_button;

use bootstrap_components::bs_well::well;
use seed::prelude::*;

use iml_duration_picker::{self, duration_picker};
use iml_grafana_chart::{grafana_chart, GRAFANA_DASHBOARD_ID, GRAFANA_DASHBOARD_NAME};
use iml_toggle::toggle;
use seed::{class, div, dom_types::At, h4, style};

/// Record from the `chroma_core_stratagemconfiguration` table
#[derive(Debug, Default, Clone, serde::Serialize, serde::Deserialize)]
pub struct StratagemConfiguration {
    pub id: u32,
    pub filesystem_id: u32,
    pub interval: u64,
    pub report_duration: Option<u64>,
    pub purge_duration: Option<u64>,
    pub immutable_state: bool,
    pub state: String,
}

#[derive(Debug, Default, Clone, serde::Serialize, serde::Deserialize)]
pub struct StratagemUpdate {
    pub id: u32,
    pub filesystem: u32,
    pub interval: u64,
    pub report_duration: Option<u64>,
    pub purge_duration: Option<u64>,
}

#[derive(Debug)]
pub struct Model {
    pub id: Option<u32>,
    pub destroyed: bool,
    pub fs_id: u32,
    pub run_config: iml_duration_picker::Model,
    pub report_active: bool,
    pub report_config: iml_duration_picker::Model,
    pub purge_active: bool,
    pub purge_config: iml_duration_picker::Model,
    pub inode_table: inode_table::Model,
    pub enable_stratagem_button: enable_stratagem_button::Model,
    pub delete_stratagem_button: delete_stratagem_button::Model,
    pub update_stratagem_button: update_stratagem_button::Model,
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
            id: None,
            fs_id: 1,
            run_config: iml_duration_picker::Model {
                value: "30".into(),
                exclude_units: vec![
                    iml_duration_picker::Unit::Minutes,
                    iml_duration_picker::Unit::Seconds,
                ],
                tooltip_placement: iml_tooltip::TooltipPlacement::Left,
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
            enable_stratagem_button: enable_stratagem_button::Model::default(),
            delete_stratagem_button: delete_stratagem_button::Model::default(),
            update_stratagem_button: update_stratagem_button::Model::default(),
        }
    }
}

impl Model {
    fn get_stratagem_update_config(&self) -> Option<StratagemUpdate> {
        if let Some(id) = self.id {
            let interval = self.run_config.value.parse::<u64>();

            if let Ok(interval) = interval {
                let report_duration: Option<u64> = match self.report_config.disabled {
                    false => self.report_config.value.parse::<u64>().ok(),
                    true => None,
                };

                let purge_duration: Option<u64> = match self.purge_config.disabled {
                    false => self.purge_config.value.parse::<u64>().ok(),
                    true => None,
                };

                Some(StratagemUpdate {
                    id,
                    filesystem: self.fs_id,
                    interval,
                    report_duration,
                    purge_duration,
                })
            } else {
                None
            }
        } else {
            None
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
    EnableStratagemButton(enable_stratagem_button::Msg),
    DeleteStratagemButton(delete_stratagem_button::Msg),
    UpdateStratagemButton(update_stratagem_button::Msg),
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
                model.id = Some(c.id);
                model.enable_stratagem_button.fs_id = model.fs_id;
                model.delete_stratagem_button.config_id = c.id;

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
                model.id = None;
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
        Msg::EnableStratagemButton(msg) => {
            model.enable_stratagem_button.fs_id = model.fs_id;
            model.enable_stratagem_button.disabled =
                model.run_config.value.parse::<u64>().ok().is_some();
            seed::log!(format!(
                "set disabled to: {}, {}",
                model.run_config.value,
                model.run_config.value.parse::<u64>().ok().is_some()
            ));

            *_orders = call_update(
                enable_stratagem_button::update,
                msg,
                &mut model.enable_stratagem_button,
            )
            .map_message(Msg::EnableStratagemButton);
        }
        Msg::DeleteStratagemButton(msg) => {
            *_orders = call_update(
                delete_stratagem_button::update,
                msg,
                &mut model.delete_stratagem_button,
            )
            .map_message(Msg::DeleteStratagemButton);
        }
        Msg::UpdateStratagemButton(msg) => {
            model.update_stratagem_button.config_data = model.get_stratagem_update_config();
            *_orders = call_update(
                update_stratagem_button::update,
                msg,
                &mut model.update_stratagem_button,
            )
            .map_message(Msg::UpdateStratagemButton);
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
            "grid-column" => "1 / span 12",
            "grid-row-end" => "1"
        }
    ]
}

fn detail_panel<T>(children: Vec<El<T>>) -> El<T> {
    well(children)
        .add_style("display".into(), "grid".into())
        .add_style(
            "grid-template-columns".into(),
            "8.33% 8.33% 8.33% 8.33% 8.33% 8.33% 8.33% 8.33% 8.33% 8.33% 8.33% 8.33%".into(),
        )
        .add_style("grid-row-gap".into(), px(20))
}

fn detail_label<T>(content: &str) -> El<T> {
    div![
        content,
        style! {
            "font-weight" => "700",
            "color" => "#777",
            "grid-column" => "1 /span 6"
        }
    ]
}

fn stratagem_section<T>(el: El<T>) -> El<T> {
    el.add_style("margin-bottom".into(), "20px".into())
}

// View
pub fn view(model: &Model) -> El<Msg> {
    let mut configuration_component = vec![
        detail_header("Stratagem Configuration"),
        detail_label("Scan filesystem every"),
        div![
            class!["input-group"],
            style! {"grid-column" => "7 /span 3", "padding-right" => "15px"},
            duration_picker(&model.run_config).map_message(Msg::RunConfig)
        ],
        detail_label("Generate report on files older than"),
        div![
            class!["input-group"],
            style! {"grid-column" => "7 /span 3", "padding-right" => "15px"},
            duration_picker(&model.report_config).map_message(Msg::ReportConfig)
        ],
        toggle(!model.report_config.disabled)
            .map_message(Msg::ToggleReport)
            .add_style("grid-column".into(), "10 /span 3".into()),
        detail_label("Purge Files older than"),
        div![
            class!["input-group"],
            style! {"grid-column" => "7 /span 3", "padding-right" => "15px"},
            duration_picker(&model.purge_config).map_message(Msg::PurgeConfig)
        ],
        toggle(!model.purge_config.disabled)
            .map_message(Msg::TogglePurge)
            .add_style("grid-column".into(), "10 /span 3".into()),
    ];

    if model.configured {
        configuration_component.extend(vec![
            update_stratagem_button::view(&model.update_stratagem_button)
                .add_style("grid-column".into(), "1 /span 12".into())
                .map_message(Msg::UpdateStratagemButton),
            delete_stratagem_button::view(&model.delete_stratagem_button)
                .add_style("grid-column".into(), "1 /span 12".into())
                .map_message(Msg::DeleteStratagemButton),
        ]);

        div![
            h4![class!["section-header"], "Stratagem"],
            stratagem_section(div!(vec![grafana_chart(
                GRAFANA_DASHBOARD_ID,
                GRAFANA_DASHBOARD_NAME,
                "10s",
                2,
                "100%",
                "600"
            )])),
            stratagem_section(inode_table::view(&model.inode_table).map_message(Msg::InodeTable)),
            detail_panel(configuration_component)
        ]
    } else {
        configuration_component.extend(vec![enable_stratagem_button::view(
            &model.enable_stratagem_button,
        )
        .add_style("grid-column".into(), "1 /span 12".into())
        .map_message(Msg::EnableStratagemButton)]);

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
