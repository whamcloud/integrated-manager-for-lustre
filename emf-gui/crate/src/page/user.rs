// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    components::{font_awesome_outline, panel, toast},
    extensions::RequestExt as _,
    generated::css_classes::C,
    GMsg,
};
use emf_wire_types::db::AuthUserRecord;
use seed::{prelude::*, *};
use std::sync::Arc;

async fn update_user(x: AuthUserRecord) -> Result<Msg, Msg> {
    fetch::Request::api_item("user", x.id)
        .with_auth()
        .method(fetch::Method::Patch)
        .send_json(&x)
        .fetch(|x| Msg::SubmitResp(Box::new(x)))
        .await
}

#[derive(Clone, Debug)]
pub enum Msg {
    Submit,
    SubmitResp(Box<fetch::FetchObject<()>>),
    SetUser(Arc<AuthUserRecord>),
    UsernameChange(String),
    FirstNameChange(String),
    LastNameChange(String),
    EmailChange(String),
    Toast(toast::Msg),
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::Submit => {
            model.logging_in = true;

            orders.perform_cmd(update_user(model.edited_user.clone()));
        }
        Msg::SubmitResp(x) => {
            model.logging_in = false;

            match x.response() {
                Ok(_) => {
                    model.toast = Some(toast::Model::Success(format!("{} updated", model.user.username)));
                    orders.send_g_msg(GMsg::UpdatePageTitle);
                }
                Err(e) => {
                    error!("An error has occurred {:?}", e);

                    model.toast = Some(toast::Model::Error(format!(
                        "There was an issue updating {}. Please try later.",
                        model.user.username
                    )));
                }
            }
        }
        Msg::Toast(x) => match x {
            toast::Msg::Close => {
                model.toast = None;
            }
        },
        Msg::SetUser(user) => {
            model.edited_user = (*user).clone();
            model.user = user;
            orders.send_g_msg(GMsg::UpdatePageTitle);
        }
        Msg::UsernameChange(x) => model.edited_user.username = x,
        Msg::FirstNameChange(x) => model.edited_user.first_name = x,
        Msg::LastNameChange(x) => model.edited_user.last_name = x,
        Msg::EmailChange(x) => model.edited_user.email = x,
    }
}

pub struct Model {
    pub user: Arc<AuthUserRecord>,
    edited_user: AuthUserRecord,
    logging_in: bool,
    toast: Option<toast::Model>,
}

impl Model {
    pub fn title(&self) -> String {
        match (self.user.first_name.as_str(), self.user.last_name.as_str()) {
            ("", "") => self.user.username.clone(),
            ("", l) => l.into(),
            (f, "") => f.into(),
            (f, l) => format!("{} {}", f, l),
        }
    }
    pub fn new(user: Arc<AuthUserRecord>) -> Self {
        Self {
            edited_user: (*user).clone(),
            user,
            logging_in: false,
            toast: None,
        }
    }
    fn disabled(&self) -> bool {
        self.edited_user == *self.user || self.logging_in
    }
}

pub fn view(model: &Model) -> impl View<Msg> {
    let input_cls = class![
        C.appearance_none,
        C.focus__outline_none,
        C.focus__shadow_outline,
        C.px_3,
        C.py_2,
        C.rounded_sm,
        C.text_gray_800,
        C.bg_gray_200,
    ];

    panel::view(
        h3![class![C.py_4, C.font_normal, C.text_lg], "User: ", &model.user.username],
        div![
            div![
                class![C.text_center, C.p_4, C.h_20],
                if let Some(x) = model.toast.as_ref() {
                    toast::view(x).map_msg(Msg::Toast)
                } else {
                    empty![]
                },
            ],
            form![
                class![C.grid, C.grid_cols_2, C.gap_4, C.p_4],
                ev(Ev::Submit, move |event| {
                    event.prevent_default();
                    Msg::Submit
                }),
                label![
                    class![C.text_gray_700, C.grid, C.content_center],
                    attrs! { At::For => "username" },
                    "Username",
                ],
                input![
                    &input_cls,
                    input_ev(Ev::Input, Msg::UsernameChange),
                    attrs! {
                        At::Id => "username",
                        At::Type => "text",
                        At::AutoFocus => true.as_at_value(),
                        At::Required => true.as_at_value(),
                        At::Value => &model.edited_user.username,
                    },
                ],
                label![
                    class![C.text_gray_700, C.grid, C.content_center],
                    attrs! { At::For => "first_name" },
                    "First Name",
                ],
                input![
                    &input_cls,
                    input_ev(Ev::Input, Msg::FirstNameChange),
                    attrs! {
                        At::Id => "first_name",
                        At::Type => "text",
                        At::Value => &model.edited_user.first_name
                    },
                ],
                label![
                    class![C.text_gray_700, C.grid, C.content_center],
                    attrs! { At::For => "last_name" },
                    "Last Name",
                ],
                input![
                    &input_cls,
                    input_ev(Ev::Input, Msg::LastNameChange),
                    attrs! {
                        At::Id => "last_name",
                        At::Type => "text",
                        At::Value => &model.edited_user.last_name
                    },
                ],
                label![
                    class![C.text_gray_700, C.grid, C.content_center],
                    attrs! { At::For => "email" },
                    "Email",
                ],
                input![
                    &input_cls,
                    input_ev(Ev::Input, Msg::EmailChange),
                    attrs! {
                        At::Id => "email",
                        At::Type => "email",
                        At::Value => &model.edited_user.email
                    },
                ],
                button![
                    class![
                        C.bg_gray_500 => model.disabled(),
                        C.cursor_not_allowed => model.disabled(),
                        C.bg_blue_500 => !model.disabled(),
                        C.hover__bg_blue_700 => !model.disabled(),
                        C.text_white,
                        C.py_2,
                        C.px_6,
                        C.rounded_sm,
                        C.focus__outline_none,
                        C.col_span_2
                    ],
                    attrs! {
                        At::Disabled => model.disabled().as_at_value()
                    },
                    font_awesome_outline(class![C.h_4, C.w_4, C.mr_1, C.inline], "check-circle"),
                    "Save",
                ],
            ]
        ],
    )
}
