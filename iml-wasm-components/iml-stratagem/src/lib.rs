// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

mod delete_stratagem_button;
mod enable_stratagem_button;
mod inode_error;
pub mod inode_table;
pub mod scan_now;
mod update_stratagem_button;

use bootstrap_components::bs_well::well;
use futures::Future;
use iml_duration_picker::{self, duration_picker};
use iml_environment::MAX_SAFE_INTEGER;
use iml_grafana_chart::{
    grafana_chart, GrafanaChartData, GRAFANA_DASHBOARD_ID, GRAFANA_DASHBOARD_NAME,
};
use iml_utils::dispatch_custom_event;
use seed::{attrs, class, div, dom_types::At, fetch, h4, input, p, prelude::*, style};

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

#[derive(Debug, Default, Clone, serde::Serialize)]
pub struct StratagemEnable {
    pub filesystem: u32,
    pub interval: u64,
    pub report_duration: Option<u64>,
    pub purge_duration: Option<u64>,
}

#[derive(Debug, Default, Clone, serde::Serialize)]
pub struct StratagemUpdate {
    pub id: u32,
    pub filesystem: u32,
    pub interval: u64,
    pub report_duration: Option<u64>,
    pub purge_duration: Option<u64>,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ActionResponse {
    command: iml_wire_types::Command,
}

#[derive(Debug, Default)]
pub struct Model {
    pub id: Option<u32>,
    pub destroyed: bool,
    pub fs_id: u32,
    pub fs_name: String,
    pub run_config: iml_duration_picker::Model,
    pub report_config: iml_duration_picker::Model,
    pub purge_config: iml_duration_picker::Model,
    pub inode_table: inode_table::Model,
    pub disabled: bool,
}

pub fn max_value_validation(ms: u64, unit: iml_duration_picker::Unit) -> Option<String> {
    if ms > MAX_SAFE_INTEGER {
        Some(format!(
            "Duration cannot be greater than {} {}",
            iml_duration_picker::convert_ms_to_unit(unit, MAX_SAFE_INTEGER),
            unit
        ))
    } else {
        None
    }
}

impl Model {
    fn get_stratagem_update_config(&self) -> Option<StratagemUpdate> {
        Some(StratagemUpdate {
            id: self.id?,
            filesystem: self.fs_id,
            interval: self.run_config.value_as_ms()?,
            report_duration: self.report_config.value_as_ms(),
            purge_duration: self.purge_config.value_as_ms(),
        })
    }

    fn create_enable_stratagem_model(&self) -> Option<StratagemEnable> {
        Some(StratagemEnable {
            filesystem: self.fs_id,
            interval: self.run_config.value_as_ms()?,
            report_duration: self.report_config.value_as_ms(),
            purge_duration: self.purge_config.value_as_ms(),
        })
    }

    fn config_valid(&self) -> bool {
        self.run_config.validation_message.is_none()
            && self.report_config.validation_message.is_none()
            && self.purge_config.validation_message.is_none()
    }

    /// Validates the input fields for the duration picker.
    /// It would be much better if we relied on HTML5 validation,
    /// but we need a solution to https://github.com/David-OConnor/seed/issues/82 first.
    fn validate(&mut self) {
        self.run_config.validation_message = match self.run_config.value_as_ms() {
            Some(ms) => {
                log::trace!("ms: {}, max: {}", ms, MAX_SAFE_INTEGER);

                if ms < 1 {
                    Some("Value must be greater than or equal to 1.".into())
                } else {
                    max_value_validation(ms, self.run_config.unit)
                }
            }
            None => Some("Please fill out this field.".into()),
        };

        let check = self
            .report_config
            .value
            .and_then(|r| self.purge_config.value.map(|p| r >= p))
            .unwrap_or(false);

        if check {
            self.report_config.validation_message =
                Some("Report duration must be less than Purge duration.".into());
        } else {
            self.report_config.validation_message = None;
        }
    }
}

#[derive(Clone, Debug)]
pub enum Command {
    Update,
    Delete,
    Enable,
}

// Update
#[derive(Clone, Debug)]
pub enum Msg {
    Destroy,
    RunConfig(iml_duration_picker::Msg),
    SetConfig(Option<StratagemConfiguration>),
    ReportConfig(iml_duration_picker::Msg),
    PurgeConfig(iml_duration_picker::Msg),
    InodeTable(inode_table::Msg),
    SendCommand(Command),
    CmdSent(fetch::FetchObject<ActionResponse>),
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg>) {
    match msg {
        Msg::Destroy => model.destroyed = true,
        Msg::RunConfig(msg) => {
            iml_duration_picker::update(msg, &mut model.run_config);
            model.validate();
        }
        Msg::ReportConfig(msg) => {
            iml_duration_picker::update(msg, &mut model.report_config);
            model.validate();
        }
        Msg::PurgeConfig(msg) => {
            iml_duration_picker::update(msg, &mut model.purge_config);
            model.validate();
        }
        Msg::SetConfig(config) => match config {
            Some(c) => {
                model.id = Some(c.id);

                iml_duration_picker::calculate_value_and_unit(&mut model.run_config, c.interval);

                match c.report_duration {
                    None => {
                        model.report_config.value = None;
                    }
                    Some(x) => {
                        iml_duration_picker::calculate_value_and_unit(&mut model.report_config, x);
                    }
                }

                match c.purge_duration {
                    None => {
                        model.purge_config.value = None;
                    }
                    Some(x) => {
                        iml_duration_picker::calculate_value_and_unit(&mut model.purge_config, x);
                    }
                }

                model.validate();
            }
            None => {
                model.id = None;
                model.run_config.value = None;
                model.report_config.value = None;
                model.purge_config.value = None;

                model.validate();
            }
        },
        Msg::InodeTable(msg) => {
            inode_table::update(
                msg,
                &mut model.inode_table,
                &mut orders.proxy(Msg::InodeTable),
            );
        }
        Msg::SendCommand(cmd) => {
            model.disabled = true;
            match cmd {
                Command::Update => {
                    if let Some(x) = &model.get_stratagem_update_config() {
                        orders.perform_cmd(
                            update_stratagem_button::update_stratagem(&x)
                                .map(Msg::CmdSent)
                                .map_err(Msg::CmdSent),
                        );
                    }
                }
                Command::Enable => {
                    if let Some(x) = &model.create_enable_stratagem_model() {
                        orders.perform_cmd(
                            enable_stratagem_button::enable_stratagem(&x)
                                .map(Msg::CmdSent)
                                .map_err(Msg::CmdSent),
                        );
                    }
                }
                Command::Delete => {
                    if let Some(x) = model.id {
                        orders.perform_cmd(
                            delete_stratagem_button::delete_stratagem(x)
                                .map(Msg::CmdSent)
                                .map_err(Msg::CmdSent),
                        );
                    }
                }
            }
        }
        Msg::CmdSent(fetch_object) => match fetch_object.response() {
            Ok(response) => {
                log::trace!("Response data: {:#?}", response.data);
                dispatch_custom_event("show_command_modal", &response.data);
                orders.skip();
            }
            Err(fail_reason) => {
                model.disabled = false;
                log::error!("Fetch error: {:#?}", fail_reason);
            }
        },
    }

    log::trace!("Model: {:#?}", model);
}

fn detail_header<T>(header: &str) -> Node<T> {
    h4![
        header,
        style! {
            "color" => "#777",
            "grid-column" => "1 / span 12",
            "grid-row-end" => "1"
        }
    ]
}

fn detail_panel<T>(children: Vec<Node<T>>) -> Node<T> {
    well(children)
        .add_style("display", "grid")
        .add_style("grid-template-columns", "repeat(11, 1fr) minmax(90px, 1fr)")
        .add_style("grid-row-gap", px(20))
}

fn detail_label<T>(content: &str) -> Node<T> {
    div![
        content,
        style! {
            "font-weight" => "700",
            "color" => "#777",
            "grid-column" => "1 /span 6"
        }
    ]
}

// View
pub fn view(model: &Model) -> Node<Msg> {
    let mut configuration_component = vec![
        detail_header("Configure Scanning Interval"),
        detail_label("Scan filesystem every"),
        div![
            class!["input-group"],
            style! {"grid-column" => "7 /span 6"},
            duration_picker(
                &model.run_config,
                input![attrs! { At::Required => true, At::Placeholder => "Required" }],
            )
            .map_message(Msg::RunConfig)
        ],
        detail_label("Generate report on files older than"),
        div![
            class!["input-group"],
            style! {"grid-column" => "7 /span 6"},
            duration_picker(
                &model.report_config,
                input![attrs! { At::Placeholder => "Optional" }]
            )
            .map_message(Msg::ReportConfig)
        ],
        detail_label("Purge Files older than"),
        div![
            class!["input-group"],
            style! {"grid-column" => "7 /span 6"},
            duration_picker(
                &model.purge_config,
                input![attrs! { At::Placeholder => "Optional" }]
            )
            .map_message(Msg::PurgeConfig)
        ],
    ];

    if model.id.is_some() {
        configuration_component.push(
            update_stratagem_button::view(model.config_valid(), model.disabled)
                .add_style("grid-column", "1 /span 12")
                .map_message(Msg::SendCommand),
        );

        configuration_component.push(
            delete_stratagem_button::view(model.config_valid(), model.disabled)
                .add_style("grid-column", "1 /span 12")
                .map_message(Msg::SendCommand),
        );
    } else {
        configuration_component.push(
            enable_stratagem_button::view(model.config_valid(), model.disabled)
                .add_style("grid-column", "1 /span 12")
                .map_message(Msg::SendCommand),
        )
    }

    div![
        inode_table::view(&model.inode_table)
            .add_style("margin-bottom", px(20))
            .map_message(Msg::InodeTable),
        h4![class!["section-header"], "File Size Distribution"],
        p![
            class!["text-muted"],
            if let Some(dt) = &model.inode_table.last_known_scan {
                format!("Last Scanned: {}", dt)
            } else {
                "No scan recorded.".into()
            }
        ],
        div![grafana_chart(
            GRAFANA_DASHBOARD_ID,
            GRAFANA_DASHBOARD_NAME,
            "100%",
            "600",
            GrafanaChartData {
                org_id: 1,
                var_fs_name: &model.fs_name,
                refresh: "10s",
                panel_id: 2,
            }
        )],
        h4![class!["section-header"], "Space Usage Distribution"],
        p![
            class!["text-muted"],
            if let Some(dt) = &model.inode_table.last_known_scan {
                format!("Last Scanned: {}", dt)
            } else {
                "No scan recorded.".into()
            }
        ],
        div![
            grafana_chart(
                GRAFANA_DASHBOARD_ID,
                GRAFANA_DASHBOARD_NAME,
                "100%",
                "600",
                GrafanaChartData {
                    org_id: 1,
                    var_fs_name: &model.fs_name,
                    refresh: "10s",
                    panel_id: 3,
                }
            ),
            style! {"margin-bottom" => px(20)}
        ],
        detail_panel(configuration_component),
    ]
}
