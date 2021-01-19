// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    components::{
        action_dropdown::{state_change, DryRun},
        command_modal, font_awesome, modal,
    },
    extensions::{MergeAttrs, NodeExt},
    generated::css_classes::C,
    key_codes, GMsg, RequestExt,
};
use emf_wire_types::{warp_drive::ErasedRecord, AvailableAction, CmdWrapper, Command, EndpointName};
use seed::{prelude::*, *};
use std::sync::Arc;

#[derive(serde::Serialize)]
pub struct SendJob<'a, T> {
    pub class_name: &'a Option<String>,
    pub args: &'a T,
}

#[derive(serde::Serialize)]
pub struct SendCmd<'a, T> {
    pub jobs: Vec<SendJob<'a, T>>,
    pub message: String,
}

#[derive(Default, Debug)]
pub struct Model {
    pub modal: modal::Model,
}

#[derive(Clone, Debug)]
pub enum Msg {
    SendJob(String, Arc<AvailableAction>),
    JobSent(Box<fetch::ResponseDataResult<Command>>),
    SendStateChange(Arc<AvailableAction>, Arc<dyn ErasedRecord>),
    StateChangeSent(Box<fetch::ResponseDataResult<CmdWrapper>>),
    Modal(modal::Msg),
    Noop,
}

#[derive(Debug)]
pub enum Action {
    Loading,
    Job(String, Arc<AvailableAction>, Arc<dyn ErasedRecord>),
    StateChange(DryRun, Arc<AvailableAction>, Arc<dyn ErasedRecord>),
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::SendJob(message, action) => {
            let x = SendCmd {
                jobs: vec![SendJob {
                    class_name: &action.class_name,
                    args: &action.args,
                }],
                message,
            };

            let req = fetch::Request::api_call(Command::endpoint_name())
                .with_auth()
                .method(fetch::Method::Post)
                .send_json(&x);

            orders
                .perform_cmd(req.fetch_json_data(|x| Msg::JobSent(Box::new(x))))
                .send_msg(Msg::Modal(modal::Msg::Close));
        }
        Msg::JobSent(data_result) => match *data_result {
            Ok(command) => {
                let x = command_modal::Input::Commands(vec![Arc::new(command)]);

                orders.send_g_msg(GMsg::OpenCommandModal(x));
            }
            Err(err) => {
                error!("An error has occurred in Msg::JobSent: {:?}", err);
                orders.skip();
            }
        },
        Msg::SendStateChange(action, erased_record) => {
            let req = state_change(&action, &erased_record, false);

            orders
                .perform_cmd(req.fetch_json_data(|x| Msg::StateChangeSent(Box::new(x))))
                .send_msg(Msg::Modal(modal::Msg::Close));
        }
        Msg::StateChangeSent(data_result) => match *data_result {
            Ok(holder) => {
                let x = command_modal::Input::Commands(vec![Arc::new(holder.command)]);

                orders.send_g_msg(GMsg::OpenCommandModal(x));
            }
            Err(err) => {
                error!("An error has occurred in Msg::StateChangeSent: {:?}", err);
                orders.skip();
            }
        },
        Msg::Modal(msg) => {
            modal::update(msg, &mut model.modal, &mut orders.proxy(Msg::Modal));
        }
        Msg::Noop => {}
    };
}

pub(crate) fn view(action: &Action) -> Node<Msg> {
    let confirm_msg = match action {
        Action::Loading => Msg::Noop,
        Action::Job(_, action, erased_record) => {
            Msg::SendJob(format!("{} {}", action.verb, erased_record.label()), Arc::clone(action))
        }
        Action::StateChange(_, action, erased_record) => {
            Msg::SendStateChange(Arc::clone(action), Arc::clone(erased_record))
        }
    };

    let confirm_msg2 = confirm_msg.clone();

    modal::bg_view(
        true,
        Msg::Modal,
        modal::content_view(
            Msg::Modal,
            match action {
                Action::Loading => vec![
                    modal::title_view(Msg::Modal, span!["Calculating Required Changes"]),
                    div![
                        class![C.my_12, C.text_center, C.text_gray_500],
                        font_awesome(class![C.w_12, C.h_12, C.inline, C.pulse], "spinner")
                    ],
                    modal::footer_view(vec![cancel_button()]).merge_attrs(class![C.pt_8]),
                ],
                Action::Job(body, action, erased_record) => {
                    let title = format!("{} {}", action.verb, erased_record.label());
                    vec![
                        modal::title_view(Msg::Modal, span![title]),
                        span![El::from_html(body)],
                        modal::footer_view(vec![
                            confirm_button().with_listener(simple_ev(Ev::Click, confirm_msg)),
                            cancel_button(),
                        ])
                        .merge_attrs(class![C.pt_8]),
                    ]
                }
                Action::StateChange(dry_run, action, erased_record) => {
                    let title = format!("{}: {}", action.verb, erased_record.label());
                    vec![
                        modal::title_view(Msg::Modal, span![title]),
                        state_change_body_view(dry_run),
                        modal::footer_view(vec![
                            confirm_button().with_listener(simple_ev(Ev::Click, confirm_msg)),
                            cancel_button(),
                        ])
                        .merge_attrs(class![C.pt_8]),
                    ]
                }
            },
        ),
    )
    .with_listener(keyboard_ev(Ev::KeyDown, move |ev| match ev.key_code() {
        key_codes::ESC => Msg::Modal(modal::Msg::Close),
        key_codes::ENTER => confirm_msg2,
        _ => Msg::Noop,
    }))
    .merge_attrs(class![C.text_black])
}

fn state_change_body_view<T>(dry_run: &DryRun) -> Node<T> {
    let job = &dry_run.transition_job;
    let dep_jobs = &dry_run.dependency_jobs;

    let desc = match job.confirmation_prompt.as_ref() {
        Some(x) => x,
        None => &job.description,
    };

    div![
        El::from_html(desc),
        if dep_jobs.is_empty() {
            empty![]
        } else {
            div![
                div![
                    class![C.py_4, C.font_medium],
                    "The following changes will also be performed"
                ],
                ul![
                    class![C.list_disc],
                    dep_jobs
                        .iter()
                        .map(|x| &x.description)
                        .map(|x| li![class![C.ml_4], x])
                        .collect::<Vec<_>>()
                ]
            ]
        }
    ]
}

fn cancel_button() -> Node<Msg> {
    seed::button![
        class![
            C.bg_transparent,
            C.py_2,
            C.px_4,
            C.rounded_full,
            C.text_blue_500,
            C.hover__bg_gray_100,
            C.hover__text_blue_400,
        ],
        simple_ev(Ev::Click, modal::Msg::Close),
        "Cancel",
    ]
    .map_msg(Msg::Modal)
}

fn confirm_button() -> Node<Msg> {
    seed::button![
        class![
            C.bg_blue_500,
            C.py_2,
            C.px_4,
            C.rounded_full,
            C.text_white,
            C.hover__bg_blue_400,
            C.mr_2,
        ],
        "Confirm",
    ]
}
