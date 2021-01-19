// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    components::{activity_indicator, date},
    ctx_help::CtxHelp,
    extensions::MergeAttrs as _,
    font_awesome, font_awesome_outline,
    generated::css_classes::C,
    page::{activity, logs},
    restrict,
    route::Route,
    GMsg, HELP_PATH,
};
use emf_wire_types::{
    warp_drive::{ArcCache, Locks},
    GroupType, Session,
};
use seed::{prelude::*, *};

#[derive(Default)]
pub struct Model {
    section: Option<Section>,
}

pub enum Section {
    Activity(activity::Model),
    Logs(logs::Model),
}

#[derive(Clone, PartialEq, Debug)]
pub enum SectionSelector {
    Activity,
    Logs,
}

impl From<SectionSelector> for Section {
    fn from(section: SectionSelector) -> Self {
        match section {
            SectionSelector::Activity => Self::Activity(activity::Model::default()),
            SectionSelector::Logs => Self::Logs(logs::Model::default()),
        }
    }
}

impl From<&Section> for SectionSelector {
    fn from(section: &Section) -> Self {
        match section {
            Section::Activity(_) => Self::Activity,
            Section::Logs(_) => Self::Logs,
        }
    }
}

#[derive(Clone, Debug)]
pub enum Msg {
    ActivitySection(activity::Msg),
    LogsSection(logs::Msg),
    Open(SectionSelector),
    Close,
}

pub fn update(msg: Msg, records: &ArcCache, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::Open(section) => {
            if model.section.as_ref().map(|x| x.into()).as_ref() == Some(&section) {
                orders.send_msg(Msg::Close);
                return;
            }

            let section = section.into();

            match &section {
                Section::Activity(_) => activity::init(&mut orders.proxy(Msg::ActivitySection)),
                Section::Logs(_) => logs::init(&mut orders.proxy(Msg::LogsSection)),
            }

            model.section = Some(section);
        }
        Msg::Close => {
            model.section = None;
        }
        Msg::ActivitySection(msg) => {
            if let Some(Section::Activity(x)) = &mut model.section {
                activity::update(msg, records, x, &mut orders.proxy(Msg::ActivitySection))
            }
        }
        Msg::LogsSection(msg) => {
            if let Some(Section::Logs(x)) = &mut model.section {
                logs::update(msg, x, &mut orders.proxy(Msg::LogsSection))
            }
        }
    }
}

fn toggle_section(model: &Model) -> Node<Msg> {
    let (icon, msg) = match model.section.as_ref() {
        Some(_) => ("chevron-right", Msg::Close),
        None => ("chevron-left", Msg::Open(SectionSelector::Activity)),
    };

    div![
        class![C.flex, C.justify_center],
        a![
            class![C.cursor_pointer],
            simple_ev(Ev::Click, msg),
            font_awesome(class![C.inline, C.w_4, C.h_4, C.text_gray_700, C.mt_6], icon)
        ]
    ]
}

pub fn view(
    model: &Model,
    route: &Route,
    cache: &ArcCache,
    activity_health: &activity_indicator::ActivityHealth,
    session: Option<&Session>,
    all_locks: &Locks,
    sd: &date::Model,
) -> Node<Msg> {
    div![
        class![
            C.z_30,
            C.flex,
            C.lg__fixed => model.section.is_some(),
            C.lg__right_0 => model.section.is_some()
        ],
        div![
            class![
                C.flex,
                C.flex_col,
                C.bg_blue_1000,
                C.lg__w_24,
                C.lg__h_main_content,
                C.hidden,
                C.lg__grid,
                C.lg__grid_rows_4,
            ],
            toggle_section(model),
            side_panel_buttons(session, route, activity_health).merge_attrs(class![C.row_span_2])
        ],
        // Status interaction panel
        match model.section.as_ref() {
            Some(Section::Activity(x)) => {
                section_container(
                    activity::view(x, session, all_locks, sd)
                        .els()
                        .map_msg(Msg::ActivitySection),
                )
            }
            Some(Section::Logs(x)) => {
                section_container(logs::view(x, cache).els().map_msg(Msg::LogsSection))
            }
            None => empty![],
        }
    ]
}

fn side_panel_buttons(
    session: Option<&Session>,
    route: &Route,
    activity_health: &activity_indicator::ActivityHealth,
) -> Node<Msg> {
    div![
        class![C.grid, C.grid_rows_3],
        div![
            class![
                // C.bg_menu_active => model.route == Route::Activity,
                C.flex,
                C.flex_col,
                C.group,
                C.items_center,
                C.justify_center,
                C.text_gray_500
                // C.text_gray_500 => model.route != Route::Activity,
                // C.text_white => model.route == Route::Activity,
            ],
            a![
                class![C.cursor_pointer],
                simple_ev(Ev::Click, Msg::Open(SectionSelector::Activity)),
                activity_indicator::view(activity_health),
            ],
            a![
                class![C.text_sm, C.group_hover__text_active, C.pt_2, C.cursor_pointer],
                simple_ev(Ev::Click, Msg::Open(SectionSelector::Activity)),
                "Activity"
            ]
        ],
        restrict::view(
            session,
            GroupType::FilesystemAdministrators,
            div![
                class![
                    // C.bg_menu_active => model.route == Route::Logs,
                    C.flex,
                    C.flex_col,
                    C.group,
                    C.items_center,
                    C.justify_center,
                ],
                a![
                    class![C.cursor_pointer],
                    simple_ev(Ev::Click, Msg::Open(SectionSelector::Logs)),
                    font_awesome(class![C.h_8, C.w_8, C.text_pink_600], "book"),
                ],
                a![
                    class![C.text_sm, C.group_hover__text_active, C.text_gray_500, C.pt_2],
                    simple_ev(Ev::Click, Msg::Open(SectionSelector::Logs)),
                    "Logs"
                ]
            ]
        ),
        div![
            class![C.flex, C.flex_col, C.group, C.justify_center, C.items_center],
            context_sensitive_help_link(route).els()
        ]
    ]
}

fn section_container(children: impl View<Msg>) -> Node<Msg> {
    div![
        class![
            C.flex,
            C.flex_col,
            C.bg_blue_1000,
            C.lg__h_main_content,
            C.pt_6,
            C.overflow_y_scroll,
            C.flex_grow,
            C.w_132
        ],
        children.els()
    ]
}

fn context_sensitive_help_link<T: 'static>(route: &Route) -> impl View<T> {
    let at = attrs! {
       At::Target => "_blank", // open the link in a new tab
       At::Href => format!(
           "/{}/docs/Graphical_User_Interface_9_0.html{}",
           HELP_PATH,
           route.help_link().unwrap_or_else(|| "".into())
       )
    };

    nodes![
        a![
            &at,
            font_awesome_outline(class![C.h_8, C.w_8, C.text_blue_400], "question-circle")
        ],
        a![
            &at,
            class![C.text_sm, C.group_hover__text_active, C.text_gray_500, C.pt_2],
            "Help"
        ]
    ]
}
