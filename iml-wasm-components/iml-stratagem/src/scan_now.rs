// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::ActionResponse;
use bootstrap_components::{bs_button, bs_modal};
use futures::Future;
use iml_duration_picker::duration_picker;
use iml_environment::csrf_token;
use iml_utils::dispatch_custom_event;
use seed::{attrs, class, div, dom_types::At, fetch, form, h4, i, input, label, prelude::*};

#[derive(Debug, serde::Serialize)]
pub struct StratagemScan {
    pub filesystem: u32,
    pub report_duration: Option<u64>,
    pub purge_duration: Option<u64>,
}

#[derive(Debug, Default)]
pub struct Model {
    pub data: Option<StratagemScan>,
    pub open: bool,
    pub disabled: bool,
    pub is_locked: bool,
    pub report_config: iml_duration_picker::Model,
    pub purge_config: iml_duration_picker::Model,
}

impl Model {
    /// Validates the input fields for the duration picker.
    /// It would be much better if we relied on HTML5 validation,
    /// but we need a solution to https://github.com/David-OConnor/seed/issues/82 first.
    fn validate(&mut self) {
        let check = self
            .report_config
            .value
            .and_then(|r| self.purge_config.value.map(|p| r >= p))
            .unwrap_or(false);

        if check {
            self.report_config.validation_message =
                Some("Report duration must be less than Purge duration.".into());
        }
    }
}

#[derive(Clone, Debug)]
pub enum Msg {
    ScanStratagem(u32),
    OpenModal,
    CloseModal,
    ReportConfig(iml_duration_picker::Msg),
    PurgeConfig(iml_duration_picker::Msg),
    StratagemScanned(fetch::FetchObject<ActionResponse>),
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg>) {
    match msg {
        Msg::ScanStratagem(filesystem) => {
            model.disabled = true;

            let x = StratagemScan {
                filesystem,
                purge_duration: model.purge_config.value_as_ms(),
                report_duration: model.report_config.value_as_ms(),
            };

            orders.perform_cmd(scan(&x));
        }
        Msg::StratagemScanned(fetch_object) => {
            model.open = false;

            match fetch_object.response() {
                Ok(response) => {
                    dispatch_custom_event("show_command_modal", &response.data);
                }
                Err(fail_reason) => {
                    model.disabled = false;
                    log::error!("Fetch error: {:#?}", fail_reason);
                }
            }
        }
        Msg::ReportConfig(msg) => {
            iml_duration_picker::update(msg, &mut model.report_config);
            model.validate();
        }
        Msg::PurgeConfig(msg) => {
            iml_duration_picker::update(msg, &mut model.purge_config);
            model.validate();
        }
        Msg::OpenModal => {
            model.open = true;
        }
        Msg::CloseModal => {
            model.open = false;
        }
    }
}

fn scan(x: &StratagemScan) -> impl Future<Item = Msg, Error = Msg> {
    seed::fetch::Request::new("/api/run_stratagem/")
        .method(seed::fetch::Method::Post)
        .header(
            "X-CSRFToken",
            &csrf_token().expect("Couldn't get csrf token."),
        )
        .send_json(x)
        .fetch_json(Msg::StratagemScanned)
}

pub fn view(fs_id: u32, model: &Model) -> Vec<Node<Msg>> {
    let mut scan_now_button = bs_button::btn(
        class![bs_button::BTN_PRIMARY],
        vec![
            Node::new_text("Scan Filesystem Now"),
            i![class!["far", "fa-chart-bar"]],
        ],
    )
    .add_style("margin-left", px(15));

    if !model.disabled && !model.is_locked {
        scan_now_button = scan_now_button.add_listener(simple_ev(Ev::Click, Msg::OpenModal));
    } else {
        scan_now_button = scan_now_button.add_attr(At::Disabled.as_str(), "disabled");
    }

    let mut xs = vec![scan_now_button];

    if model.open {
        xs.append(&mut scan_modal(fs_id, &model));
    }

    xs
}

fn scan_modal(fs_id: u32, model: &Model) -> Vec<Node<Msg>> {
    let mut scan_button = bs_button::btn(
        class![bs_button::BTN_SUCCESS],
        vec![Node::new_text(if model.disabled {
            "Scanning..."
        } else if model.is_locked {
            "Locked 🔒"
        } else {
            "Scan Now"
        })],
    )
    .add_listener(mouse_ev(Ev::Click, move |_| Msg::ScanStratagem(fs_id)));

    if model.disabled || model.is_locked {
        scan_button = scan_button.add_attr("disabled", true);
    }

    vec![
        bs_modal::backdrop(),
        bs_modal::modal(vec![
            bs_modal::header(vec![h4![
                "Scan Filesystem Now ",
                i![class!["far", "fa-chart-bar"]]
            ]]),
            bs_modal::body(vec![form![
                div![
                    class!["form-group"],
                    label!["Generate report for files older than"],
                    div![
                        class!["input-group"],
                        duration_picker(
                            &model.report_config,
                            input![attrs! {At::AutoFocus => true, At::Placeholder => "Optional"}]
                        )
                        .map_message(Msg::ReportConfig)
                    ],
                ],
                div![
                    class!["form-group"],
                    label!["Purge Files older than"],
                    div![
                        class!["input-group"],
                        duration_picker(
                            &model.purge_config,
                            input![attrs! {At::Placeholder => "Optional"}]
                        )
                        .map_message(Msg::PurgeConfig)
                    ],
                ],
            ]]),
            bs_modal::footer(vec![
                scan_button,
                bs_button::btn(
                    class![bs_button::BTN_DEFAULT],
                    vec![
                        Node::new_text("Close"),
                        i![class!["far", "fa-times-circle"]],
                    ],
                )
                .add_listener(simple_ev(Ev::Click, Msg::CloseModal)),
            ]),
        ]),
    ]
}
