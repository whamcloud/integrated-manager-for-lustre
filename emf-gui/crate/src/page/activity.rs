// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    components::{action_dropdown, command_modal, date, font_awesome, loading, paging},
    extensions::*,
    generated::css_classes::C,
    sleep_with_handle, GMsg,
};
use emf_api_utils::extract_id;
use emf_wire_types::{
    warp_drive::{ArcCache, Locks},
    Alert, AlertRecordType, AlertSeverity, ApiList, EndpointName as _, Session,
};
use futures::channel::oneshot;
use seed::{prelude::*, *};
use std::{collections::HashMap, mem, time::Duration};

enum State {
    Loading,
    Fetching,
    Loaded(ApiList<Alert>, HashMap<i32, Row>),
}

struct Row {
    dropdown: action_dropdown::Model,
}

pub struct Model {
    state: State,
    cancel: Option<oneshot::Sender<()>>,
    pager: paging::Model,
}

impl Default for Model {
    fn default() -> Self {
        Self {
            state: State::Loading,
            cancel: None,
            pager: paging::Model::default(),
        }
    }
}

#[derive(Clone, Debug)]
pub enum Msg {
    ActionDropdown(Box<action_dropdown::IdMsg>),
    ActionsFetched(Box<fetch::ResponseDataResult<ApiList<Alert>>>),
    OpenCommandModal(i32),
    FetchOffset,
    Loop,
    Page(paging::Msg),
    Noop,
}

pub fn update(msg: Msg, cache: &ArcCache, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::FetchOffset => {
            if let Ok(cmd) = fetch::Request::api_query(
                Alert::endpoint_name(),
                &[("limit", model.pager.limit()), ("offset", model.pager.offset())],
            )
            .map(|req| req.fetch_json_data(|x| Msg::ActionsFetched(Box::new(x))))
            {
                orders.skip().perform_cmd(cmd);
            } else {
                error!("Could not fetch alerts.");
            };
        }
        Msg::ActionsFetched(r) => {
            let state = mem::replace(&mut model.state, State::Loading);

            model.state = match (*r, state) {
                (Ok(mut resp), State::Loaded(_, mut rows)) => {
                    update_rows(&mut resp, &mut rows);

                    orders
                        .proxy(Msg::Page)
                        .send_msg(paging::Msg::SetTotal(resp.meta.total_count as usize));

                    State::Loaded(resp, rows)
                }
                (Ok(mut resp), State::Fetching) => {
                    let mut rows = HashMap::new();

                    update_rows(&mut resp, &mut rows);

                    State::Loaded(resp, rows)
                }
                (Ok(mut resp), State::Loading) => {
                    let mut rows = HashMap::new();

                    update_rows(&mut resp, &mut rows);

                    orders
                        .proxy(Msg::Page)
                        .send_msg(paging::Msg::SetTotal(resp.meta.total_count as usize));

                    State::Loaded(resp, rows)
                }
                (Err(fail_reason), state) => {
                    error!("An error has occurred {:?}", fail_reason);
                    orders.skip();

                    state
                }
            };

            orders.send_msg(Msg::Loop);
        }
        Msg::ActionDropdown(msg) => {
            let action_dropdown::IdMsg(id, msg) = *msg;

            if let State::Loaded(_, rows) = &mut model.state {
                if let Some(x) = rows.get_mut(&id) {
                    action_dropdown::update(
                        action_dropdown::IdMsg(id, msg),
                        cache,
                        &mut x.dropdown,
                        &mut orders.proxy(|x| Msg::ActionDropdown(Box::new(x))),
                    );
                }
            }
        }
        Msg::OpenCommandModal(id) => {
            orders.send_g_msg(GMsg::OpenCommandModal(command_modal::Input::Ids(vec![id])));
        }
        Msg::Page(msg) => match model.state {
            State::Fetching => {
                orders.skip();
            }
            _ => {
                paging::update(msg.clone(), &mut model.pager, &mut orders.proxy(Msg::Page));

                match msg {
                    paging::Msg::Next | paging::Msg::Prev => {
                        model.state = State::Fetching;
                        orders.send_msg(Msg::FetchOffset);
                    }
                    _ => {}
                }
            }
        },
        Msg::Loop => {
            orders.skip();

            let (cancel, fut) = sleep_with_handle(Duration::from_secs(10), Msg::FetchOffset, Msg::Noop);

            model.cancel = Some(cancel);

            orders.perform_cmd(fut);
        }
        Msg::Noop => {}
    }
}

pub(crate) fn init(orders: &mut impl Orders<Msg, GMsg>) {
    orders
        .proxy(Msg::Page)
        .send_msg(paging::Msg::SetLimit(paging::ROW_OPTS[1]));
    orders.send_msg(Msg::FetchOffset);
}

fn update_rows(alerts: &mut ApiList<Alert>, rows: &mut HashMap<i32, Row>) {
    let (add, remove): (Vec<_>, Vec<_>) = alerts
        .objects
        .iter_mut()
        .partition(|x| x.active.unwrap_or_default() && !is_cmd(x.record_type));

    for x in add {
        rows.entry(x.id).or_insert(Row {
            dropdown: action_dropdown::Model::new(x.affected_composite_ids.take().unwrap_or_default()),
        });
    }

    for x in remove {
        rows.remove(&x.id);
    }
}

pub(crate) fn view(model: &Model, session: Option<&Session>, all_locks: &Locks, sd: &date::Model) -> impl View<Msg> {
    div![match &model.state {
        State::Loading => loading::view(),
        State::Fetching => div![
            class![C.bg_menu_active],
            div![
                class![C.px_6, C.py_4, C.bg_blue_1000],
                div![class![C.font_medium, C.text_lg, C.text_gray_500], "Activities"],
                div![
                    class![C.grid, C.grid_cols_2, C.items_center, C.text_white],
                    div![
                        class![C.col_span_1],
                        paging::page_count_view(&model.pager).map_msg(Msg::Page)
                    ],
                    div![
                        class![C.grid, C.grid_cols_2, C.justify_end],
                        paging::next_prev_view(&model.pager).map_msg(Msg::Page)
                    ],
                ],
            ],
            div![loading::view()]
        ],
        State::Loaded(alerts, rows) => div![
            class![C.bg_menu_active],
            div![
                class![C.px_6, C.py_4, C.bg_blue_1000],
                div![class![C.font_medium, C.text_lg, C.text_gray_500], "Activities"],
                div![
                    class![C.grid, C.grid_cols_2, C.items_center, C.text_white],
                    div![
                        class![C.col_span_1],
                        paging::page_count_view(&model.pager).map_msg(Msg::Page)
                    ],
                    div![
                        class![C.grid, C.grid_cols_2, C.justify_end],
                        paging::next_prev_view(&model.pager).map_msg(Msg::Page)
                    ]
                ],
            ],
            alerts.objects.iter().map(|x| {
                let row = rows.get(&x.id);

                alert_item_view(all_locks, sd, session, x, row)
            })
        ],
    }]
}

fn alert_icon_view(alert: &Alert) -> Node<Msg> {
    let cls = class![C.inline, C.w_4, C.h_4];

    match alert.record_type {
        AlertRecordType::AlertEvent
        | AlertRecordType::LearnEvent
        | AlertRecordType::SyslogEvent
        | AlertRecordType::StorageResourceLearnEvent => font_awesome(cls, "info-circle"),
        x if is_cmd(x) => font_awesome(cls, "terminal"),
        _ => font_awesome(cls, "bell"),
    }
}

fn is_cmd(x: AlertRecordType) -> bool {
    match x {
        AlertRecordType::CommandRunningAlert
        | AlertRecordType::CommandSuccessfulAlert
        | AlertRecordType::CommandErroredAlert
        | AlertRecordType::CommandCancelledAlert => true,
        _ => false,
    }
}

fn alert_item_classes(alert: &Alert) -> (&str, &str, &str) {
    match (alert.record_type, alert.severity) {
        (AlertRecordType::CommandRunningAlert, _) => (C.border_gray_500, C.text_gray_500, C.bg_gray_400),
        (AlertRecordType::CommandSuccessfulAlert, _) => (C.border_green_500, C.text_green_500, C.bg_green_400),
        (AlertRecordType::CommandErroredAlert, _) => (C.border_red_500, C.text_red_500, C.bg_red_400),
        (AlertRecordType::CommandCancelledAlert, _) => (C.border_gray_500, C.text_gray_500, C.bg_gray_400),
        (_, AlertSeverity::DEBUG) => (C.border_gray_500, C.text_gray_500, C.bg_gray_400),
        (_, AlertSeverity::INFO) => (C.border_blue_500, C.text_blue_500, C.bg_blue_400),
        (_, AlertSeverity::WARNING) => (C.border_yellow_500, C.text_yellow_500, C.bg_yellow_400),
        (_, AlertSeverity::ERROR) => (C.border_red_500, C.text_red_500, C.bg_red_400),
        (_, AlertSeverity::CRITICAL) => (C.border_orange_500, C.text_orange_500, C.bg_orange_400),
    }
}

fn alert_item_view(
    all_locks: &Locks,
    sd: &date::Model,
    session: Option<&Session>,
    alert: &Alert,
    row: Option<&Row>,
) -> Node<Msg> {
    let (border_color, icon_color, bg_color) = alert_item_classes(alert);

    let is_active = alert.active.unwrap_or_default();

    div![
        class![
            border_color,
            bg_color => is_active,
            C.bg_menu => !is_active,
            C.border_l_8,
            C.gap_4,
            C.grid_cols_3,
            C.grid_flow_row,
            C.grid,
            C.items_center,
            C.mx_4,
            C.my_6,
            C.p_4,
            C.rounded,
            C.text_white,
        ],
        div![class![C.row_span_1, C.col_span_2], alert.message],
        div![
            class![C.row_span_1, C.col_span_1, C.grid, C.justify_end],
            alert_icon_view(alert).merge_attrs(class![icon_color])
        ],
        div![
            class![C.row_span_1, C.col_span_2, C.whitespace_no_wrap],
            "Started",
            " ",
            date_view(sd, &alert.begin)
        ],
        div![
            class![C.row_span_1, C.col_span_1, C.grid, C.justify_end],
            if let Some(row) = row {
                action_dropdown::unstyled_view(
                    alert.id,
                    &row.dropdown,
                    all_locks,
                    session,
                    class![C.bg_transparent, C.border, C.border_white],
                )
                .map_msg(|x| Msg::ActionDropdown(Box::new(x)))
            } else {
                empty![]
            }
        ],
        div![
            class![C.row_span_1, C.col_span_2, C.whitespace_no_wrap],
            if let Some(end) = alert.end.as_ref() {
                span!["Ended ", date_view(sd, end)]
            } else {
                empty![]
            }
        ],
        command_details_button(alert),
    ]
}

fn date_view<T>(sd: &date::Model, date: &str) -> Node<T> {
    match chrono::DateTime::parse_from_rfc3339(date) {
        Ok(d) => date::view(sd, &d),
        Err(e) => {
            error!(format!("could not parse the date: '{}': {}", date, e));
            plain![date.to_string()]
        }
    }
}

fn command_details_button(alert: &Alert) -> Node<Msg> {
    if !is_cmd(alert.record_type) {
        return empty![];
    }

    if let Some(id) = extract_id(&alert.alert_item) {
        button![
            class![
                C.border_white,
                C.border,
                C.focus__outline_none,
                C.font_bold,
                C.px_4,
                C.py_2,
                C.rounded,
                C.text_white
            ],
            simple_ev(Ev::Click, Msg::OpenCommandModal(id.parse().unwrap())),
            "Details",
        ]
    } else {
        empty![]
    }
}
