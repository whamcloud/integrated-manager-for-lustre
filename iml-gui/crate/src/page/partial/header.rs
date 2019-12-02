use crate::{
    components::font_awesome, generated::css_classes::C, Model, Msg, Page,
    Visibility::*,
};
use seed::{prelude::*, *};

fn menu_icon<T>(icon_name: &str) -> Node<T> {
    font_awesome(class![C.h_6, C.w_6, C.mr_3, C.inline], icon_name)
}

fn nav_configure_dropdown(open: bool) -> Node<Msg> {
    if !open {
        return seed::empty();
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
            C.z_20
        ],
        style! { "top" => "110%" },
        ul![
            li![a![
                &cls,
                "Servers",
                attrs! {
                    At::Href => Page::Server.to_href(),
                },
            ]],
            li![
                a![&cls, "Power Control"],
                attrs! {
                    At::Href => Page::PowerControl.to_href(),
                },
            ],
            li![
                a![&cls, "Filesystems"],
                attrs! {
                    At::Href => Page::Filesystem.to_href(),
                },
            ],
            li![a![&cls, "HSM"]],
            li![a![&cls, "Storage"]],
            li![
                a![&cls, "Users"],
                attrs! {
                    At::Href => Page::User.to_href(),
                },
            ],
            li![
                a![&cls, "Volumes"],
                attrs! {
                    At::Href => Page::Volume.to_href(),
                },
            ],
            li![
                a![&cls, "MGTs"],
                attrs! {
                    At::Href => Page::Mgt.to_href(),
                },
            ]
        ]
    ]
}

fn main_menu_items(model: &Model) -> Node<Msg> {
    let menu_class = class![
        C.block,
        C.lg__h_16,
        C.lg__inline_block,
        C.lg__flex,
        C.lg__flex_auto,
        C.lg__flex_col,
        C.lg__justify_center,
        C.lg__py_0,
        C.p_6,
        C.text_gray_500,
        C.hover__bg_menu_active,
        C.border_b_2,
        C.border_transparent,
        C.group,
    ];

    div![
        class![C.text_base, C.lg__flex, C.lg__h_16,],
        a![
            &menu_class,
            class![C.bg_menu_active => model.page == Page::Dashboard],
            attrs! {
                At::Href => Page::Dashboard.to_href()
            },
            span![
                menu_icon("tachometer-alt"),
                span![
                    class![C.group_hover__text_active, C.text_active => model.page == Page::Dashboard],
                    "Dashboard"
                ],
            ]
        ],
        a![
            &menu_class,
            class![
                C.lg__border_blue_400 => model.config_menu_state.is_open(),
                C.relative
            ],
            simple_ev(Ev::Click, Msg::ConfigMenuState),
            span![
                menu_icon("cog"),
                span![
                    class![C.group_hover__text_active],
                    "Configuration",
                    font_awesome(
                        class![C.fill_current, C.h_3, C.w_3, C.ml_1, C.inline],
                        "chevron-down"
                    ),
                ],
            ],
            nav_configure_dropdown(model.config_menu_state.is_open()),
        ],
        a![
            &menu_class,
            class![C.bg_menu_active => model.page == Page::Jobstats],
            attrs! {
                At::Href => Page::Jobstats.to_href()
            },
            span![
                menu_icon("signal"),
                span![
                    class![C.group_hover__text_active, C.text_active => model.page == Page::Jobstats],
                    "Jobstats"
                ],
            ]
        ],
        a![
            &menu_class,
            class![C.bg_menu_active => model.page == Page::Logs],
            attrs! {
                At::Href => Page::Logs.to_href()
            },
            span![
                menu_icon("book"),
                span![
                    class![C.group_hover__text_active, C.bg_menu_active => model.page == Page::Logs],
                    "Logs"
                ]
            ]
        ],
        a![
            &menu_class,
            attrs! {
                At::Href => "#responsive-header",
            },
            span![
                menu_icon("question-circle"),
                span![class![C.group_hover__text_active], "Help"]
            ]
        ],
        a![
            &menu_class,
            class![C.bg_menu_active => model.page == Page::Activity],
            attrs! {
                At::Href => Page::Activity.to_href(),
            },
            span![
                class![C.group_hover__text_active, C.bg_menu_active => model.page == Page::Activity],
                "Activity",
            ]
        ],
    ]
}

fn nav(model: &Model) -> Node<Msg> {
    nav![
        class![
            C.flex,
            C.bg_menu,
            C.items_center,
            C.px_5,
            C.lg__h_16,
            C.justify_between,
            C.flex_wrap
        ],
        div![
            class![
                C.flex,
                C.items_center,
                C.flex_shrink_0,
                C.text_white,
                C.mr_12,
            ],
            svg![
                class![C.fill_current, C.h_8, C.w_8, C.mr_3,],
                attrs! {
                    At::ViewBox => "0 0 335.77 299.14",
                },
                path![
                    attrs! { At::D => "M184,25.14c2.54,16.11,22.53,31.32,13,56-2.56,1.48-3.15,2.4-7,3-1.36-1.26-1.77-1.37-4-2-6.35-22.69-10.52-44.68-28-56-27.6-17.87-73.46.61-80,25,19.84,1,27.55,14.55,38,25,18.55,18.55,40.14,34.84,56,56l15,14c6.31,8.43,10,22.79,3,34-4.18,6.65-33.83,18.8-47,16-5.81-1.24-26-9-26-9-2.62,4.1-4,13.52-5,18-4.57,1.22-7.7,2.07-13,1l-1-3c-5.52-7.71,5.49-12.11,3-22-4.06-16.11-22.4-24.7-23-41,2.43-1.53,4.86-5.51,9-5,5.84.71,11.38,9.38,15,13,10.53,10.53,22.39,25.08,38,30,8.69,2.74,34.49-4.58,37-10v-7c-13.82-10.62-26.06-28.69-39-41-18-17.14-37.87-33-55-51-14.2.39-15.43,10.45-29,8-1-4-2-7-2-13,5.49-7.82,6.84-18.13,12-26,12.26-18.71,45.37-45.06,82-35,9.05,2.49,16.71,9,26,10,14-13.38,53.26-17.42,75-8,33.49,14.52,48.41,39.69,48,89,14.89,4.64,33.8,29.18,39,44,3.19,9.09,1.58,37.66-1,46-6.57,21.27-22.49,37.66-42,46-8.7,3.72-55.05,12.78-60,1-1.05-1.55-1-4.09-1-7,4.93-3.27,8.65-4.18,18-4,5.93-3.48,18,0,25-2a110.2,110.2,0,0,0,25-11c12.15-7.25,26.16-40.39,19-64-2.14-7.06-8.05-12.7-12-18-4.36-5.84-8.78-13.19-18-14-6.77,11.6-25.37,31.92-43,32-2.72-4-4.83-3.89-5-11,14.48-9.26,33.39-23.18,39-41v-14c0-32.21-21.78-51-46-59C213,11.82,196.87,22.86,184,25.14Zm-150,132c5.47,0,8.49,1,10,5,.8,1.18.77,1.68,1,4-8.87,9.33-24.11,33.77-38,36-2.44-2.52-4.66-3.16-6-7-.75-1.07-.6-.95-1-3,1.79-2.1,2.31-4.72,4-7C11.93,174.41,24.69,166.66,34,157.14Zm34,70h4c1.94,2.83,5.64,6.61,4,10-1.47,7.62-28.59,31.76-38,32-2.56-3.3-3.88-2.59-4-9,6.11-5.82,10.43-14.78,17-20C56.52,235.75,62.93,232,68,227.14Zm120,1h7c2.64,3.93,4.05,4.61,4,12l-43,43c-5.81,5.81-10.64,15-21,16-2.2-2.09-3.69-1.72-5-5-1-1.42-1-3.27-1-6a245.4,245.4,0,0,0,27-30Z", },
                ],
            ],
            span![class![C.font_semibold, C.text_3xl, C.tracking_tight], "IML"],
        ],
        div![
            class![C.block, C.lg__hidden,],
            button![
                class![
                    C.flex,
                    C.items_center,
                    C.px_3,
                    C.py_2,
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
                        At::ViewBox => "0 0 20 20",
                    },
                    title!["Menu",],
                    path![
                        attrs! { At::D => "M0 3h20v2H0V3zm0 6h20v2H0V9zm0 6h20v2H0v-2z", },
                    ],
                ],
            ],
        ],
        if model.menu_visibility == Visible {
            div![
                class![
                    C.w_full,
                    C.block,
                    C.flex_grow,
                    C.lg__flex,
                    C.lg__items_center,
                    C.lg__w_auto,
                    C.lg__h_16,
                ],
                main_menu_items(&model),
                div![
                    class![
                        C.text_base,
                        C.lg__flex,
                        C.lg__h_16,
                        C.lg__flex_grow,
                        C.lg__justify_end
                    ],
                    a![
                        class![
                            C.block,
                            C.lg__h_16,
                            C.lg__inline_block,
                            C.lg__flex,
                            C.lg__flex_auto,
                            C.lg__flex_col,
                            C.lg__flex_grow_0,
                            C.lg__justify_center,
                            C.lg__py_0,
                            C.p_6,
                            C.text_gray_300,
                            C.hover__text_white,
                            C.border_b_2,
                            C.border_transparent
                        ],
                        attrs! {
                            At::Href => Page::Login.to_href(),
                        },
                        "Login",
                    ],
                ],
            ]
        } else {
            empty![]
        }
    ]
}

pub fn view(model: &Model) -> impl View<Msg> {
    vec![
        header![nav(&model)],
        div![
            class![
                C.bg_menu_active,
                C.text_gray_300,
                C.text_base,
                C.text_center,
                C.py_2
            ],
            model.page.to_string()
        ],
    ]
}
