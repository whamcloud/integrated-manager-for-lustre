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
use iml_environment::MAX_SAFE_INTEGER;
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
#[derive(Debug, Default, Clone)]
pub struct Validation {
    run_config: Option<String>,
    report_config: Option<String>,
    purge_config: Option<String>,
}

impl Validation {
    fn is_valid(&self) -> bool {
        self.run_config.is_none() && self.report_config.is_none() && self.purge_config.is_none()
    }
}

pub enum Durations {
    RunConfig,
    ReportConfig,
    PurgeConfig,
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
                disabled: false,
                ..Default::default()
            },
            purge_config: iml_duration_picker::Model {
                value: "30".into(),
                exclude_units: vec![
                    iml_duration_picker::Unit::Minutes,
                    iml_duration_picker::Unit::Seconds,
                ],
                disabled: false,
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

fn max_value_validation(ms: u64, unit: iml_duration_picker::Unit) -> Option<String> {
    if ms > MAX_SAFE_INTEGER {
        Some(format!(
            "Duration cannot be greater than {} {}",
            iml_duration_picker::convert_ms_to_unit(unit, MAX_SAFE_INTEGER),
            unit.to_string()
        ))
    } else {
        None
    }
}

impl Model {
    fn get_stratagem_update_config(&self) -> Option<StratagemUpdate> {
        if let Some(id) = self.id {
            let interval = self.run_config.value.parse::<u64>();

            if let Ok(interval) = interval {
                let interval_ms =
                    iml_duration_picker::convert_unit_to_ms(self.run_config.unit, interval);
                let report_duration: Option<u64> = match self.report_config.disabled {
                    false => self
                        .report_config
                        .value
                        .parse::<u64>()
                        .map(|x| {
                            iml_duration_picker::convert_unit_to_ms(self.report_config.unit, x)
                        })
                        .ok(),
                    true => None,
                };

                let purge_duration: Option<u64> = match self.purge_config.disabled {
                    false => self
                        .purge_config
                        .value
                        .parse::<u64>()
                        .map(|x| iml_duration_picker::convert_unit_to_ms(self.purge_config.unit, x))
                        .ok(),
                    true => None,
                };

                Some(StratagemUpdate {
                    id,
                    filesystem: self.fs_id,
                    interval: interval_ms,
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

    fn validate(&mut self) -> Validation {
        let mut validation = Validation {
            ..Default::default()
        };

        let run_config = self.run_config.value.parse::<u64>();
        if run_config.clone().is_err() {
            validation.run_config =
                Some("The report field must contain a numeric value.".to_string());
        } else {
            let val = run_config.clone().unwrap();
            let ms = iml_duration_picker::convert_unit_to_ms(self.run_config.unit, val);
            seed::log!("ms: {}, max: {}", ms, MAX_SAFE_INTEGER);
            validation.run_config = max_value_validation(ms, self.run_config.unit);
        }

        let report_config = self.report_config.value.parse::<u64>();

        if self.report_config.disabled {
            validation.report_config = None;
        } else if report_config.clone().is_err() {
            validation.report_config =
                Some("The report field must contain a numeric value.".to_string());
        } else {
            let val = report_config.clone().unwrap();
            let ms = iml_duration_picker::convert_unit_to_ms(self.report_config.unit, val);

            validation.report_config = max_value_validation(ms, self.report_config.unit);
        }

        let purge_config = self.purge_config.value.parse::<u64>();
        if self.purge_config.disabled {
            validation.purge_config = None;
        } else if purge_config.clone().is_err() {
            validation.purge_config =
                Some("The purge field must contain a numeric value.".to_string());
        } else {
            let val = purge_config.clone().unwrap();
            let ms = iml_duration_picker::convert_unit_to_ms(self.report_config.unit, val);

            validation.report_config = max_value_validation(ms, self.report_config.unit);
        }

        if report_config.is_ok()
            && purge_config.is_ok()
            && report_config.unwrap() > purge_config.unwrap()
        {
            validation.report_config =
                Some("Report duration must be less than Purge duration.".to_string());
        }

        if self.run_config.validation_message.is_none() {
            self.run_config.validation_message = validation.run_config.clone();
        }

        if self.report_config.validation_message.is_none() {
            self.report_config.validation_message = validation.report_config.clone();
        }

        if self.purge_config.validation_message.is_none() {
            self.purge_config.validation_message = validation.purge_config.clone();
        }

        validation
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
        Msg::RunConfig(msg) => {
            iml_duration_picker::update(msg, &mut model.run_config);

            let validation = model.validate();
            model.enable_stratagem_button.disabled = !validation.is_valid();
        }
        Msg::ReportConfig(msg) => {
            iml_duration_picker::update(msg, &mut model.report_config);
            let validation = model.validate();
            model.enable_stratagem_button.disabled = !validation.is_valid();
        }
        Msg::PurgeConfig(msg) => {
            iml_duration_picker::update(msg, &mut model.purge_config);
            let validation = model.validate();

            model.enable_stratagem_button.disabled = !validation.is_valid();
        }
        Msg::ToggleReport(iml_toggle::Active(active)) => {
            model.report_config.disabled = !active;
            let validation = model.validate();

            model.enable_stratagem_button.disabled = !validation.is_valid();
        }
        Msg::TogglePurge(iml_toggle::Active(active)) => {
            model.purge_config.disabled = !active;
            let validation = model.validate();

            model.enable_stratagem_button.disabled = !validation.is_valid();
        }
        Msg::SetConfig(config) => match config {
            Some(c) => {
                model.configured = true;
                model.id = Some(c.id);
                model.enable_stratagem_button.fs_id = model.fs_id;
                model.enable_stratagem_button.disabled = true;

                model.delete_stratagem_button.config_id = c.id;

                model.run_config.value = iml_duration_picker::convert_ms_to_unit(
                    iml_duration_picker::Unit::Days,
                    c.interval,
                )
                .to_string();
                model.report_active = c.report_duration.is_some();
                match c.report_duration {
                    None => {
                        model.report_config.value = "".to_string();
                        model.report_config.disabled = true;
                    }
                    Some(x) => {
                        model.report_config.value = iml_duration_picker::convert_ms_to_unit(
                            iml_duration_picker::Unit::Days,
                            x,
                        )
                        .to_string()
                    }
                }

                model.purge_active = c.purge_duration.is_some();
                match c.purge_duration {
                    None => {
                        model.purge_config.value = "".to_string();
                        model.purge_config.disabled = true;
                    }
                    Some(x) => {
                        model.purge_config.value = iml_duration_picker::convert_ms_to_unit(
                            iml_duration_picker::Unit::Days,
                            x,
                        )
                        .to_string()
                    }
                }

                model.validate();
            }
            None => {
                model.configured = false;
                model.id = None;
                model.run_config.value = "".to_string();
                model.report_active = false;
                model.report_config.value = "".to_string();
                model.report_config.disabled = false;
                model.purge_active = false;
                model.purge_config.value = "".to_string();
                model.purge_config.disabled = false;
                model.enable_stratagem_button.fs_id = model.fs_id;

                model.enable_stratagem_button.disabled = true;
                model.validate();
            }
        },
        Msg::InodeTable(msg) => {
            *_orders = call_update(inode_table::update, msg, &mut model.inode_table)
                .map_message(Msg::InodeTable);
        }
        Msg::EnableStratagemButton(msg) => {
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
            style! {"grid-column" => "7 /span 6"},
            duration_picker(&model.run_config).map_message(Msg::RunConfig)
        ],
        detail_label("Generate report on files older than"),
        div![
            class!["input-group"],
            style! {"grid-column" => "7 /span 5", "padding-right" => "15px"},
            duration_picker(&model.report_config).map_message(Msg::ReportConfig)
        ],
        toggle(!model.report_config.disabled)
            .map_message(Msg::ToggleReport)
            .add_style("grid-column".into(), "12".into()),
        detail_label("Purge Files older than"),
        div![
            class!["input-group"],
            style! {"grid-column" => "7 /span 5", "padding-right" => "15px"},
            duration_picker(&model.purge_config).map_message(Msg::PurgeConfig)
        ],
        toggle(!model.purge_config.disabled)
            .map_message(Msg::TogglePurge)
            .add_style("grid-column".into(), "12".into()),
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
