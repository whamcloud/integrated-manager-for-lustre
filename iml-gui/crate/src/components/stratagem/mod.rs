use crate::{components::duration_picker, environment, extensions::MergeAttrs, generated::css_classes::C, GMsg};
use futures::TryFutureExt;
use iml_wire_types::{db::StratagemConfiguration, Filesystem};
use seed::{prelude::*, *};
use std::sync::Arc;

pub(crate) mod delete_stratagem_button;
pub(crate) mod enable_stratagem_button;
pub(crate) mod inode_table;
pub(crate) mod update_stratagem_button;

pub struct Model {
    pub inode_table: inode_table::Model,
    pub stratagem_config: Arc<StratagemConfiguration>,
    pub filesystem: Arc<Filesystem>,
    pub scan_duration_picker: duration_picker::Model,
    pub report_duration_picker: duration_picker::Model,
    pub purge_duration_picker: duration_picker::Model,
    pub id: Option<u32>,
    pub destroyed: bool,
    pub disabled: bool,
    pub is_locked: bool,
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

impl Model {
    pub fn new(
        inode_table: inode_table::Model,
        filesystem: Arc<Filesystem>,
        stratagem_config: Arc<StratagemConfiguration>,
    ) -> Self {
        Model {
            inode_table,
            filesystem,
            stratagem_config,
            scan_duration_picker: duration_picker::Model::default(),
            report_duration_picker: duration_picker::Model::default(),
            purge_duration_picker: duration_picker::Model::default(),
            id: None,
            destroyed: false,
            disabled: false,
            is_locked: false,
        }
    }

    fn get_stratagem_update_config(&self) -> Option<StratagemUpdate> {
        Some(StratagemUpdate {
            id: self.id?,
            filesystem: self.filesystem.id,
            interval: self.scan_duration_picker.value_as_ms()?,
            report_duration: self.report_duration_picker.value_as_ms(),
            purge_duration: self.purge_duration_picker.value_as_ms(),
        })
    }

    fn create_enable_stratagem_model(&self) -> Option<StratagemEnable> {
        Some(StratagemEnable {
            filesystem: self.filesystem.id,
            interval: self.scan_duration_picker.value_as_ms()?,
            report_duration: self.report_duration_picker.value_as_ms(),
            purge_duration: self.purge_duration_picker.value_as_ms(),
        })
    }

    fn config_valid(&self) -> bool {
        log!(
            "scan_duration validation message",
            self.scan_duration_picker.validation_message
        );
        self.scan_duration_picker.validation_message.is_none()
            && self.report_duration_picker.validation_message.is_none()
            && self.purge_duration_picker.validation_message.is_none()
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
    InodeTable(inode_table::Msg),
    ScanDurationPicker(duration_picker::Msg),
    ReportDurationPicker(duration_picker::Msg),
    PurgeDurationPicker(duration_picker::Msg),
    SendCommand(Command),
    CmdSent(fetch::FetchObject<ActionResponse>),
    ConfigStateUpdated,
    Noop,
}

pub fn init(orders: &mut impl Orders<Msg, GMsg>) {
    orders.proxy(Msg::InodeTable).send_msg(inode_table::Msg::FetchInodes);
}

pub(crate) fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::InodeTable(x) => inode_table::update(x, &mut model.inode_table, &mut orders.proxy(Msg::InodeTable)),
        Msg::ScanDurationPicker(msg) => {
            duration_picker::update(msg, &mut model.scan_duration_picker);
            model.validate();
        }
        Msg::ReportDurationPicker(msg) => {
            duration_picker::update(msg, &mut model.report_duration_picker);
            model.validate();
        }
        Msg::PurgeDurationPicker(msg) => {
            duration_picker::update(msg, &mut model.purge_duration_picker);
            model.validate();
        }
        Msg::SendCommand(cmd) => {
            model.disabled = true;
            match cmd {
                Command::Update => {
                    if let Some(x) = model.get_stratagem_update_config() {
                        orders.perform_cmd(
                            update_stratagem_button::update_stratagem(x)
                                .map_ok(Msg::CmdSent)
                                .map_err(Msg::CmdSent),
                        );
                    }
                }
                Command::Enable => {
                    let m = model.create_enable_stratagem_model();
                    if let Some(x) = m {
                        log!("enable", x);
                        orders.perform_cmd(
                            enable_stratagem_button::enable_stratagem(x)
                                .map_ok(Msg::CmdSent)
                                .map_err(Msg::CmdSent),
                        );
                    }
                }
                Command::Delete => {
                    if let Some(x) = model.id {
                        orders.perform_cmd(
                            delete_stratagem_button::delete_stratagem(x)
                                .map_ok(Msg::CmdSent)
                                .map_err(Msg::CmdSent),
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
                model.disabled = false;
                log!("Fetch error: {:#?}", fail_reason);
            }
        },
        Msg::Noop => {}
    }
}
pub(crate) fn view(model: &Model) -> Node<Msg> {
    inode_table::view(&model.inode_table).map_msg(Msg::InodeTable)
}

pub fn config_view(model: &Model) -> Node<Msg> {
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
                        At::AutoFocus => true,
                        At::Required => true,
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
                        At::AutoFocus => true,
                        At::Required => true,
                        At::Placeholder => "Optional",
                    },
                ],
            )
            .merge_attrs(class![C.grid, C.grid_cols_6])
            .map_msg(Msg::PurgeDurationPicker)
        ],
    ];

    if model.id.is_some() {
        let mut upd_btn = update_stratagem_button::view(model.config_valid(), model.disabled || model.is_locked);
        configuration_component.push(upd_btn.map_msg(|x| Msg::SendCommand(x)));

    // let mut del_btn = delete_stratagem_button::view(model.config_valid(), model.disabled || model.is_locked);
    // del_btn.add_style("grid-column", "1 /span 12");
    // configuration_component.push(del_btn.map_message(Msg::SendCommand));
    } else {
        let mut enb_btn = enable_stratagem_button::view(model.config_valid(), model.disabled || model.is_locked)
            .merge_attrs(class![C.col_span_2]);
        configuration_component.push(enb_btn.map_msg(|x| Msg::SendCommand(x)));
    }

    div![class![C.grid, C.grid_cols_2, C.gap_2, C.p_3], configuration_component]
    //div![duration_picker::view(&model.duration_picker).map_msg(Msg::ScanDurationPicker)]
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ActionResponse {
    command: iml_wire_types::Command,
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
