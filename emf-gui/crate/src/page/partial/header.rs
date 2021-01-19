// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    auth, breakpoints,
    components::{
        ai_200x, ai_400x, ai_7990x, breadcrumbs, ddn_logo, ddn_logo_lettering, exa5, font_awesome, restrict,
        whamcloud_logo,
    },
    generated::css_classes::C,
    MergeAttrs, Model, Msg, Route, SessionExt,
    Visibility::*,
};
use emf_wire_types::{Branding, DdnBranding, GroupType};
use seed::{prelude::*, *};

fn menu_icon<T>(icon_name: &str) -> Node<T> {
    font_awesome(
        class![C.h_6, C.inline, C.lg__h_5, C.lg__mr_2, C.lg__w_5, C.mr_3, C.w_6, C.xl__h_6, C.xl__mr_3, C.xl__w_6],
        icon_name,
    )
}

fn nav_manage_dropdown(open: bool, conf: &emf_wire_types::Conf) -> Node<Msg> {
    if !open {
        return empty![];
    }

    let cls = class![
        C.my_2,
        C.px_4,
        C.py_2,
        C.bg_menu_active,
        C.block,
        C.cursor_pointer,
        C.hover__text_white,
    ];

    div![
        class![
            C.lg__absolute,
            C.lg__border,
            C.lg__w_full,
            C.lg__left_0,
            C.border_gray_600,
            C.mt_px,
            C.text_gray_500,
            C.rounded,
            C.bg_menu,
            C.p_4,
            C.z_40
        ],
        style! { "top" => "110%" },
        ul![
            li![a![
                &cls,
                "Servers",
                attrs! {
                    At::Href => Route::Servers.to_href(),
                },
            ]],
            li![
                a![&cls, "Filesystems"],
                attrs! {
                    At::Href => Route::Filesystems.to_href(),
                },
            ],
            li![
                a![&cls, "Volumes"],
                attrs! {
                    At::Href => Route::Volumes.to_href(),
                },
            ],
            li![
                a![&cls, "MGTs"],
                attrs! {
                    At::Href => Route::Mgt.to_href(),
                },
            ],
            if conf.use_snapshots {
                li![
                    a![&cls, "Snapshots"],
                    attrs! {
                        At::Href => Route::Snapshots.to_href(),
                    },
                ]
            } else {
                empty![]
            },
            if conf.use_stratagem {
                li![
                    a![&cls, "Stratagem"],
                    attrs! {
                        At::Href => Route::Stratagem.to_href(),
                    },
                ]
            } else {
                empty![]
            },
            li![
                a![&cls, "Users"],
                attrs! {
                    At::Href => Route::Users.to_href(),
                },
            ]
        ]
    ]
}

fn main_menu_items(model: &Model) -> Node<Msg> {
    let menu_class = class![
        C.block,
        C.border_b_2,
        C.border_transparent,
        C.group,
        C.hover__bg_menu_active,
        C.lg__flex_auto,
        C.lg__flex_col,
        C.lg__flex,
        C.lg__h_16,
        C.lg__inline_block,
        C.lg__justify_center,
        C.lg__p_4,
        C.lg__py_0,
        C.p_6,
        C.text_gray_500,
        C.xl__p_6,
    ];

    div![
        class![C.lg__flex, C.lg__h_16],
        a![
            &menu_class,
            class![C.bg_menu_active => model.route == Route::Dashboard],
            attrs! {
                At::Href => Route::Dashboard.to_href()
            },
            span![
                menu_icon("tachometer-alt"),
                span![
                    class![C.group_hover__text_active, C.text_active => model.route == Route::Dashboard],
                    "Dashboard",
                ],
            ]
        ],
        restrict::view(
            model.auth.get_session(),
            GroupType::FilesystemAdministrators,
            a![
                &menu_class,
                class![
                    C.lg__border_blue_400 => model.manage_menu_state.is_open(),
                    C.relative,
                    C.cursor_pointer
                ],
                simple_ev(Ev::Click, Msg::ManageMenuState),
                span![
                    menu_icon("cog"),
                    span![
                        class![C.group_hover__text_active],
                        "Management",
                        font_awesome(
                            class![C.fill_current, C.h_3, C.w_3, C.ml_1, C.inline, C._mt_1],
                            "chevron-down"
                        ),
                    ],
                ],
                nav_manage_dropdown(model.manage_menu_state.is_open(), &model.conf),
            ]
        ),
    ]
}

fn toggle_nav_view() -> Node<Msg> {
    div![
        class![C.block, C.lg__hidden],
        button![
            class![
                C.flex,
                C.items_center,
                C.px_3,
                C.py_3,
                C.border,
                C.rounded,
                C.border_gray_400,
                C.text_gray_300,
                C.hover__text_white,
                C.hover__border_white,
            ],
            simple_ev(Ev::Click, Msg::ToggleMenu),
            svg![
                class![C.fill_current, C.h_3, C.w_3],
                attrs! {
                    At::ViewBox => "0 0 20 20"
                },
                title!["Menu"],
                path![attrs! { At::D => "M0 3h20v2H0V3zm0 6h20v2H0V9zm0 6h20v2H0v-2z" }],
            ],
        ],
    ]
}

fn ddn_logo_full<T>() -> Node<T> {
    div![
        class![C.inline_flex],
        ddn_logo().merge_attrs(class![C.h_8, C.mr_1]),
        ddn_logo_lettering().merge_attrs(class![C.h_6, C.m_px])
    ]
}

/// The navbar logo
fn logo_nav_view<T>(branding: Branding) -> Node<T> {
    let (logo, txt) = match branding {
        Branding::Whamcloud => (whamcloud_logo().merge_attrs(class![C.h_12, C.w_24, C.mr_3]), empty![]),
        Branding::DDN(ddn_brand) => (
            ddn_logo_full(),
            span![
                class![C.font_semibold, C.text_2xl, C.tracking_tight, C.ml_2],
                match ddn_brand {
                    DdnBranding::AI200X => ai_200x().merge_attrs(class![C.h_8, C.mr_1]),
                    DdnBranding::AI400X => ai_400x().merge_attrs(class![C.h_8, C.mr_1]),
                    DdnBranding::AI7990X => ai_7990x().merge_attrs(class![C.h_8, C.mr_1]),
                    DdnBranding::Exascaler => exa5().merge_attrs(class![C.h_8, C.mr_1]),
                    _ => plain![ddn_brand.to_string()],
                }
            ],
        ),
    };

    div![
        class![
            C.flex_shrink_0,
            C.flex,
            C.items_center,
            C.lg__ml_0,
            C.lg__mr_4,
            C.lg__my_0,
            C.ml_6,
            C.my_2,
            C.text_white,
            C.xl__mr_12
        ],
        logo,
        txt,
    ]
}

fn nav(model: &Model) -> Node<Msg> {
    nav![
        class![
            C.flex,
            C.bg_menu,
            C.items_center,
            C.px_5,
            C.xl__px_5,
            C.lg__px_4,
            C.lg__h_16,
            C.justify_between,
            C.flex_wrap
        ],
        logo_nav_view(model.conf.branding),
        toggle_nav_view(),
        if model.menu_visibility == Visible || model.breakpoint_size >= breakpoints::Size::LG {
            div![
                class![
                    C.w_full,
                    C.block,
                    C.flex_grow,
                    C.lg__text_sm,
                    C.xl__text_base,
                    C.lg__flex,
                    C.lg__items_center,
                    C.lg__w_auto,
                    C.lg__h_16,
                ],
                main_menu_items(model),
                auth_view(&model.auth),
            ]
        } else {
            empty![]
        }
    ]
}

/// Show the logged in user if available.
/// Also show the Login / Logout link
pub fn auth_view(auth: &auth::Model) -> Node<Msg> {
    let x = match auth.get_session() {
        Some(session) => session,
        None => return empty![],
    };

    let cls = class![
        C.block,
        C.border_b_2,
        C.border_transparent,
        C.cursor_pointer
        C.hover__text_white,
        C.lg__flex_auto,
        C.lg__flex_col,
        C.lg__flex_grow_0,
        C.lg__flex,
        C.lg__h_16,
        C.lg__inline_block,
        C.lg__justify_center,
        C.lg__py_0,
        C.p_6,
        C.lg__p_4,
        C.xl__p_6,
        C.text_gray_300
    ];

    let mut auth_link = a![&cls, if !x.has_user() { "Login" } else { "Logout" }];

    let auth_link = if !x.has_user() {
        auth_link.merge_attrs(attrs! {
            At::Href => Route::Login.to_href(),
        })
    } else {
        auth_link.add_listener(simple_ev(Ev::Click, Msg::Auth(Box::new(auth::Msg::Logout))));

        auth_link
    };

    div![
        class![C.lg__flex, C.lg__h_16, C.lg__flex_grow, C.lg__justify_end],
        match x.user.as_ref() {
            Some(user) => {
                a![
                    &cls,
                    attrs! {
                        At::Href => Route::User(user.id.into()).to_href()
                    },
                    match (user.full_name.as_str(), user.username.as_str()) {
                        ("", x) => x,
                        (x, _) => x,
                    }
                ]
            }
            None => empty![],
        },
        auth_link
    ]
}

pub fn view(model: &Model) -> impl View<Msg> {
    vec![
        header![nav(model)],
        div![
            class![C.bg_menu_active, C.text_gray_300, C.text_center, C.py_2],
            breadcrumbs::view(&model.breadcrumbs).els()
        ],
    ]
}
