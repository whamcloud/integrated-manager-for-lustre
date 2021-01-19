// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    auth,
    components::{ddn_logo, ddn_logo_lettering, whamcloud_logo},
    generated::css_classes::C,
    GMsg, MergeAttrs,
};
use core::fmt;
use emf_wire_types::Branding;
use seed::{browser::service::fetch, prelude::*, *};

#[derive(Clone, Default, serde::Serialize)]
struct Form {
    username: String,
    password: String,
}

#[derive(Clone, Debug, Default, serde::Deserialize)]
pub struct Errors {
    __all__: Option<String>,
    password: Option<Vec<String>>,
    username: Option<Vec<String>>,
}

#[derive(Default)]
pub struct Model {
    errors: Option<Errors>,
    form: Form,
    logging_in: bool,
}

impl Model {
    fn disabled(&self) -> bool {
        self.form.username.is_empty() || self.form.password.is_empty() || self.logging_in
    }
}

#[allow(clippy::large_enum_variant)]
#[derive(Clone)]
pub enum Msg {
    UsernameChange(String),
    PasswordChange(String),
    SubmitResp(fetch::FetchObject<Errors>),
    Submit,
}

impl fmt::Debug for Msg {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::PasswordChange(_) => f.write_str("*****"),
            _ => write!(f, "{:?}", self),
        }
    }
}

async fn login(form: Form) -> Result<Msg, Msg> {
    auth::fetch_session()
        .method(fetch::Method::Post)
        .send_json(&form)
        .fetch_json(Msg::SubmitResp)
        .await
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::UsernameChange(x) => model.form.username = x,
        Msg::PasswordChange(x) => model.form.password = x,
        Msg::Submit => {
            model.logging_in = true;

            orders.perform_cmd(login(model.form.clone()));
        }
        Msg::SubmitResp(x) => {
            match x.result {
                Err(e) => error!("Response error {:?}", e),
                Ok(x) => {
                    if x.status.code < 400 {
                        orders.skip().send_g_msg(GMsg::AuthProxy(Box::new(auth::Msg::LoggedIn)));
                    } else {
                        model.logging_in = false;

                        match x.data {
                            Ok(x) => model.errors = Some(x),
                            Err(e) => error!("DataError {:?}", e),
                        }
                    }
                }
            };
        }
    }
}

fn err_item<T>(x: &str) -> Node<T> {
    p![class![C.text_red_500, C.text_xs, C.italic,], x]
}

pub fn view(model: &Model, branding: Branding, exa_version: &Option<String>) -> impl View<Msg> {
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

    let errs = Errors::default();

    let errs = model.errors.as_ref().unwrap_or_else(|| &errs);
    let (border_color, text_color, logo) = match branding {
        Branding::Whamcloud => (
            C.border_teal_500,
            C.text_teal_500,
            whamcloud_logo().merge_attrs(class![C.h_16, C.w_16]),
        ),
        Branding::DDN(_) => (
            C.border_red_700,
            C.text_black,
            div![
                class![C.w_32, C.flex, C.flex_col, C.items_center],
                ddn_logo().merge_attrs(class![C.w_24, C.mb_4]),
                ddn_logo_lettering().merge_attrs(class![C.w_24]),
            ],
        ),
    };
    let exa_version = if let Some(version) = exa_version {
        p![class![C.mt_3], "Version ", version]
    } else {
        empty![]
    };

    div![
        class![
            C.bg_gray_100,
            C.fade_in,
            C.flex,
            C.items_center,
            C.justify_center,
            C.min_h_screen,
        ],
        form![
            class![C.bg_white, C.shadow_md, C.px_16, C.py_8, C.border_b_8, border_color],
            ev(Ev::Submit, move |event| {
                event.prevent_default();
                Msg::Submit
            }),
            div![
                class![
                    C.flex_col,
                    C.flex,
                    C.items_center,
                    C.justify_center,
                    C.mb_6
                    text_color,
                ],
                logo,
                exa_version
            ],
            match errs.__all__.as_ref() {
                Some(x) => err_item(x),
                None => empty![],
            },
            div![
                class![C.mb_4],
                input![
                    class![C.mt_2],
                    input_ev(Ev::Input, Msg::UsernameChange),
                    &input_cls,
                    attrs! {
                        At::AutoFocus => true.as_at_value(),
                        At::Required => true.as_at_value(),
                        At::Placeholder => "Username",
                        At::AutoComplete => "username"
                    },
                ],
                match errs.username.as_ref() {
                    Some(errs) => {
                        errs.iter().map(|x| err_item(x)).collect()
                    }
                    None => vec![],
                }
            ],
            div![
                class![C.mb_6],
                input![
                    class![C.mt_2, C.mb_2],
                    input_ev(Ev::Input, Msg::PasswordChange),
                    &input_cls,
                    attrs! {
                        At::Required => true,
                        At::Type => "password",
                        At::Placeholder => "Password",
                        At::AutoComplete => "current-password"
                    },
                ],
                match errs.password.as_ref() {
                    Some(errs) => {
                        errs.iter().map(|x| err_item(x)).collect()
                    }
                    None => vec![],
                }
            ],
            div![
                class![C.flex, C.items_center, C.justify_between],
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
                        C.focus__outline_none
                    ],
                    attrs! {
                        At::Disabled => model.disabled().as_at_value()
                    },
                    "Login",
                ],
            ],
        ]
    ]
}
