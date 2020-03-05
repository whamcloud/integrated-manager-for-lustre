use crate::{
    components::{duration_picker, grafana_chart},
    environment,
    extensions::MergeAttrs,
    generated::css_classes::C,
    GMsg,
};
use futures::TryFutureExt;
use iml_wire_types::{db::StratagemConfiguration, warp_drive::ArcCache, warp_drive::Locks, Filesystem, ToCompositeId};
use seed::{prelude::*, *};
use std::collections::HashMap;
use std::sync::Arc;

pub(crate) mod delete_stratagem_button;
pub(crate) mod enable_stratagem_button;
pub(crate) mod inode_table;
pub(crate) mod scan_stratagem_button;
pub(crate) mod scan_stratagem_modal;
pub(crate) mod update_stratagem_button;

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ActionResponse {
    command: iml_wire_types::Command,
}

#[derive(Default)]
pub struct TargetConfig {
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

#[derive(Debug, Default, Clone, serde::Serialize)]
pub struct StratagemEnable {
    pub filesystem: u32,
    pub interval: u64,
    pub report_duration: Option<u64>,
    pub purge_duration: Option<u64>,
}

#[derive(Clone, Debug)]
pub enum Command {
    Update,
    Delete,
    Enable,
}

enum State {
    Disabled,
    Enabled(Box<Config>),
}

#[derive(Debug, serde::Serialize)]
pub struct StratagemScan {
    pub filesystem: u32,
    pub report_duration: Option<u64>,
    pub purge_duration: Option<u64>,
}

pub struct Model {
    fs: Arc<Filesystem>,
    state: State,
    stratagem_config: Option<Arc<StratagemConfiguration>>,
}

impl Model {
    pub fn new(fs: Arc<Filesystem>) -> Self {
        Self {
            state: State::Disabled,
            fs,
            stratagem_config: None,
        }
    }
}

pub fn filesystem_locked(fs: &Filesystem, locks: &Locks) -> bool {
    locks.get(&fs.composite_id().to_string()).is_some()
}

pub fn max_value_validation(ms: u64, unit: duration_picker::Unit) -> Option<String> {
    if ms > environment::MAX_SAFE_INTEGER {
        Some(format!(
            "Duration cannot be greater than {} {}",
            duration_picker::convert_ms_to_unit(unit, environment::MAX_SAFE_INTEGER),
            unit
        ))
    } else {
        None
    }
}

pub struct Config {
    inode_table: inode_table::Model,
    grafana_vars: HashMap<String, String>,
    pub scan_duration_picker: duration_picker::Model,
    pub report_duration_picker: duration_picker::Model,
    pub purge_duration_picker: duration_picker::Model,
    pub id: Option<u32>,
    pub destroyed: bool,
    pub disabled: bool,
    pub target_config: TargetConfig,
    pub scan_stratagem_button: scan_stratagem_button::Model,
}

impl Config {
    fn config_valid(&self) -> bool {
        self.scan_duration_picker.validation_message.is_none()
            && self.report_duration_picker.validation_message.is_none()
            && self.purge_duration_picker.validation_message.is_none()
    }
    fn get_stratagem_update_config(&self, fs_id: u32) -> Option<StratagemUpdate> {
        Some(StratagemUpdate {
            id: self.id?,
            filesystem: fs_id,
            interval: self.scan_duration_picker.value_as_ms()?,
            report_duration: self.report_duration_picker.value_as_ms(),
            purge_duration: self.purge_duration_picker.value_as_ms(),
        })
    }

    fn create_enable_stratagem_model(&self, fs_id: u32) -> Option<StratagemEnable> {
        Some(StratagemEnable {
            filesystem: fs_id,
            interval: self.scan_duration_picker.value_as_ms()?,
            report_duration: self.report_duration_picker.value_as_ms(),
            purge_duration: self.purge_duration_picker.value_as_ms(),
        })
    }
    /// Validates the input fields for the duration picker.
    /// It would be much better if we relied on HTML5 validation,
    /// but we need a solution to https://github.com/David-OConnor/seed/issues/82 first.
    pub fn validate(&mut self) {
        self.scan_duration_picker.validation_message = match self.scan_duration_picker.value_as_ms() {
            Some(ms) => {
                log!("ms: {}, max: {}", ms, environment::MAX_SAFE_INTEGER);

                if ms < 1 {
                    Some("Value must be greater than or equal to 1.".into())
                } else {
                    max_value_validation(ms, self.scan_duration_picker.unit)
                }
            }
            None => Some("Please fill out this field.".into()),
        };

        let check = self
            .report_duration_picker
            .value
            .and_then(|r| self.purge_duration_picker.value.map(|p| r >= p))
            .unwrap_or(false);

        if check {
            self.report_duration_picker.validation_message =
                Some("Report duration must be less than Purge duration.".into());
        } else {
            self.report_duration_picker.validation_message = None;
        }
    }
}

#[derive(Clone)]
pub enum Msg {
    UpdateStratagemConfig(Arc<StratagemConfiguration>),
    SetStratagemConfig(Vec<Arc<StratagemConfiguration>>),
    DeleteStratagemConfig,
    InodeTable(inode_table::Msg),
    ScanDurationPicker(duration_picker::Msg),
    ReportDurationPicker(duration_picker::Msg),
    PurgeDurationPicker(duration_picker::Msg),
    SendCommand(Command),
    CheckStratagem,
    EnableStratagem,
    DisableStratagem,
    CmdSent(Box<fetch::FetchObject<ActionResponse>>),
    ScanStratagemButton(scan_stratagem_button::Msg),
    Noop,
}

fn can_enable(fs: &Arc<Filesystem>, cache: &ArcCache) -> bool {
    let server_resources: Vec<_> = fs
        .mdts
        .iter()
        .flat_map(|x| x.failover_servers.iter().chain(std::iter::once(&x.primary_server)))
        .collect();

    let servers: Vec<_> = cache
        .host
        .values()
        .filter(|x| server_resources.contains(&&x.resource_uri))
        .collect();

    !servers.is_empty()
        && servers
            .into_iter()
            .all(|x| x.server_profile.name == "stratagem_server" || x.server_profile.name == "exascaler_server")
}

fn handle_stratagem_config_update(config: &mut Config, conf: &Arc<StratagemConfiguration>) {
    config.id = Some(conf.id);

    duration_picker::calculate_value_and_unit(&mut config.scan_duration_picker, conf.interval);

    match conf.report_duration {
        None => {
            config.report_duration_picker.value = None;
        }
        Some(x) => {
            duration_picker::calculate_value_and_unit(&mut config.report_duration_picker, x);
        }
    }

    match conf.purge_duration {
        None => {
            config.purge_duration_picker.value = None;
        }
        Some(x) => {
            duration_picker::calculate_value_and_unit(&mut config.purge_duration_picker, x);
        }
    }

    if conf.interval == config.target_config.interval
        && conf.report_duration == config.target_config.report_duration
        && conf.purge_duration == config.target_config.purge_duration
    {
        config.disabled = false;
    }

    config.validate();
}

pub(crate) fn update(msg: Msg, cache: &ArcCache, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    if let State::Enabled(config) = &mut model.state {
        match msg {
            Msg::InodeTable(x) => inode_table::update(x, &mut config.inode_table, &mut orders.proxy(Msg::InodeTable)),
            Msg::ScanDurationPicker(msg) => {
                duration_picker::update(msg, &mut config.scan_duration_picker);
                config.validate();
            }
            Msg::ReportDurationPicker(msg) => {
                duration_picker::update(msg, &mut config.report_duration_picker);
                config.validate();
            }
            Msg::PurgeDurationPicker(msg) => {
                duration_picker::update(msg, &mut config.purge_duration_picker);
                config.validate();
            }
            Msg::CheckStratagem => {
                if !can_enable(&model.fs, cache) {
                    orders.send_msg(Msg::DisableStratagem);
                }
            }
            Msg::DisableStratagem => {
                model.state = State::Disabled;
            }
            Msg::EnableStratagem => {}
            Msg::SendCommand(cmd) => {
                config.disabled = true;

                match cmd {
                    Command::Update => {
                        if let Some(x) = config.get_stratagem_update_config(model.fs.id) {
                            config.target_config = TargetConfig {
                                interval: x.interval,
                                report_duration: x.report_duration,
                                purge_duration: x.purge_duration,
                            };

                            orders.perform_cmd(
                                update_stratagem_button::update_stratagem(x)
                                    .map_ok(|x| Msg::CmdSent(Box::new(x)))
                                    .map_err(|x| Msg::CmdSent(Box::new(x))),
                            );
                        }
                    }
                    Command::Enable => {
                        let m = config.create_enable_stratagem_model(model.fs.id);
                        if let Some(x) = m {
                            config.target_config = TargetConfig {
                                interval: x.interval,
                                report_duration: x.report_duration,
                                purge_duration: x.purge_duration,
                            };

                            orders.perform_cmd(
                                enable_stratagem_button::enable_stratagem(x)
                                    .map_ok(|x| Msg::CmdSent(Box::new(x)))
                                    .map_err(|x| Msg::CmdSent(Box::new(x))),
                            );
                        }
                    }
                    Command::Delete => {
                        if let Some(x) = config.id {
                            orders.perform_cmd(
                                delete_stratagem_button::delete_stratagem(x)
                                    .map_ok(|x| Msg::CmdSent(Box::new(x)))
                                    .map_err(|x| Msg::CmdSent(Box::new(x))),
                            );
                        }
                    }
                }
            }
            Msg::CmdSent(fetch_object) => match fetch_object.response() {
                Ok(response) => {
                    log!("Response data: {:#?}", response.data);
                    // Give feedback that stratagem has been set
                    orders.skip();
                }
                Err(fail_reason) => {
                    config.disabled = false;
                    log!("Fetch error: {:#?}", fail_reason);
                }
            },
            Msg::SetStratagemConfig(conf) => {
                let id = model.fs.id;
                let matching_conf = conf.into_iter().find(|c| c.filesystem_id == id);

                if let Some(conf) = matching_conf {
                    handle_stratagem_config_update(config, &conf);
                }
            }
            Msg::UpdateStratagemConfig(conf) => {
                handle_stratagem_config_update(config, &conf);
            }
            Msg::DeleteStratagemConfig => {
                config.id = None;
                config.scan_duration_picker.value = None;
                config.report_duration_picker.value = None;
                config.purge_duration_picker.value = None;
                config.disabled = false;
                config.validate();
            }
            Msg::ScanStratagemButton(msg) => {
                scan_stratagem_button::update(
                    msg,
                    &mut config.scan_stratagem_button,
                    &mut orders.proxy(Msg::ScanStratagemButton),
                );
            }
            Msg::Noop => {}
        }
    } else {
        match msg {
            Msg::CheckStratagem => {
                if can_enable(&model.fs, cache) {
                    orders.send_msg(Msg::EnableStratagem);
                }
            }
            Msg::EnableStratagem => {
                let mut grafana_vars = HashMap::new();
                grafana_vars.insert("fs_name".into(), model.fs.name.clone());

                let mut cfg = Config {
                    inode_table: inode_table::Model::new(&model.fs.name),
                    grafana_vars,
                    scan_duration_picker: duration_picker::Model::default(),
                    report_duration_picker: duration_picker::Model::default(),
                    purge_duration_picker: duration_picker::Model::default(),
                    id: None,
                    destroyed: false,
                    disabled: false,
                    target_config: Default::default(),
                    scan_stratagem_button: scan_stratagem_button::Model::new(model.fs.id),
                };

                if let Some(conf) = &model.stratagem_config {
                    handle_stratagem_config_update(&mut cfg, &conf);
                }

                cfg.validate();

                model.state = State::Enabled(Box::new(cfg));

                orders.proxy(Msg::InodeTable).send_msg(inode_table::Msg::FetchInodes);
            }
            Msg::SetStratagemConfig(conf) => {
                let id = model.fs.id;
                model.stratagem_config = conf.into_iter().find(|c| c.filesystem_id == id);
            }
            _ => {}
        }
    }
}

pub(crate) fn view(model: &Model, all_locks: &Locks) -> Node<Msg> {
    match &model.state {
        State::Disabled => empty![],
        State::Enabled(config) => {
            let locked = filesystem_locked(&model.fs, &all_locks);

            let last_scan = format!(
                "Last Scanned: {}",
                config
                    .inode_table
                    .last_known_scan
                    .as_ref()
                    .unwrap_or(&"N/A".to_string())
            );

            div![
                scan_stratagem_button::view(&config.scan_stratagem_button).map_msg(Msg::ScanStratagemButton),
                inode_table::view(&config.inode_table).map_msg(Msg::InodeTable),
                caption_wrapper(
                    "inode Usage Distribution",
                    Some(&last_scan),
                    stratagem_chart(grafana_chart::GrafanaChartData {
                        org_id: 1,
                        refresh: "1m",
                        panel_id: 2,
                        vars: config.grafana_vars.clone()
                    })
                ),
                caption_wrapper(
                    "Space Usage Distribution",
                    Some(&last_scan),
                    stratagem_chart(grafana_chart::GrafanaChartData {
                        org_id: 1,
                        refresh: "1m",
                        panel_id: 3,
                        vars: config.grafana_vars.clone()
                    })
                ),
                stratagem_config(&config, locked)
            ]
        }
    }
}

fn stratagem_config(model: &Config, locked: bool) -> Node<Msg> {
    div![
        class![
            C.bg_white,
            C.border,
            C.border_b,
            C.border_t,
            C.mt_24,
            C.rounded_lg,
            C.shadow,
        ],
        div![
            class![C.flex, C.justify_between, C.px_6, C._mb_px, C.bg_gray_200],
            h3![class![C.py_4, C.font_normal, C.text_lg], "Configure Scanning Interval"]
        ],
        config_view(model, locked),
    ]
}

fn stratagem_chart<T>(data: grafana_chart::GrafanaChartData) -> Node<T> {
    grafana_chart::view("OBdCS5IWz", "stratagem", data, "400")
}

//TODO: move to the table module and use it where the tables are used as well:
fn caption_wrapper<T>(caption: &str, comment: Option<&str>, children: impl View<T>) -> Node<T> {
    div![
        class![
            C.bg_white,
            C.border,
            C.border_b,
            C.border_t,
            C.mt_24,
            C.rounded_lg,
            C.shadow,
        ],
        div![
            class![C.flex, C.justify_between, C.px_6, C._mb_px, C.bg_gray_200],
            h3![class![C.py_4, C.font_normal, C.text_lg], caption],
            if let Some(c) = comment {
                p![class![C.py_4, C.text_gray_600], c]
            } else {
                empty![]
            }
        ],
        children.els()
    ]
}

pub fn config_view(model: &Config, locked: bool) -> Node<Msg> {
    let input_cls = class![
        C.appearance_none,
        C.focus__outline_none,
        C.focus__shadow_outline,
        C.px_3,
        C.py_2,
        C.rounded_sm,
        C.text_gray_800,
        C.bg_gray_200,
        C.col_span_5
    ];

    let mut configuration_component = vec![
        span!["Scan filesystem every"],
        div![
            class!["input-group"],
            duration_picker::view(
                &model.scan_duration_picker,
                input![
                    &input_cls,
                    attrs! {
                        At::AutoFocus => true,
                        At::Required => true,
                        At::Placeholder => "Required",
                    },
                ],
            )
            .merge_attrs(class![C.grid, C.grid_cols_6])
            .map_msg(Msg::ScanDurationPicker)
        ],
        span!["Generate report on files older than"],
        div![
            class!["input-group"],
            duration_picker::view(
                &model.report_duration_picker,
                input![
                    &input_cls,
                    attrs! {
                        At::AutoFocus => false,
                        At::Placeholder => "Optional",
                    },
                ]
            )
            .merge_attrs(class![C.grid, C.grid_cols_6])
            .map_msg(Msg::ReportDurationPicker)
        ],
        span!["Purge Files older than"],
        div![
            class!["input-group"],
            duration_picker::view(
                &model.purge_duration_picker,
                input![
                    &input_cls,
                    attrs! {
                        At::AutoFocus => false,
                        At::Placeholder => "Optional",
                    },
                ],
            )
            .merge_attrs(class![C.grid, C.grid_cols_6])
            .map_msg(Msg::PurgeDurationPicker)
        ],
    ];

    if model.id.is_some() {
        let upd_btn = update_stratagem_button::view(model.config_valid(), model.disabled || locked);
        configuration_component.push(upd_btn.map_msg(Msg::SendCommand));

        let del_btn = delete_stratagem_button::view(model.config_valid(), model.disabled || locked);
        configuration_component.push(del_btn.map_msg(Msg::SendCommand));
    } else {
        let enb_btn = enable_stratagem_button::view(model.config_valid(), model.disabled || locked);
        configuration_component.push(enb_btn.map_msg(Msg::SendCommand));
    }

    div![class![C.grid, C.grid_cols_2, C.gap_2, C.p_3], configuration_component]
}
