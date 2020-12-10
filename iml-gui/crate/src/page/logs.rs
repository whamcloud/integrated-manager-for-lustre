// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    components::{font_awesome, loading, paging},
    extensions::*,
    generated::css_classes::C,
    route::{Route, RouteId},
    sleep::sleep_with_handle,
    GMsg,
};
use futures::channel::oneshot;
use iml_graphql_queries::{
    log::{self, logs},
    Response,
};
use iml_wire_types::{warp_drive::ArcCache, Host, LogMessage, LogSeverity, SortDir};
use seed::{prelude::*, *};
use std::{sync::Arc, time::Duration};

#[derive(Default)]
pub struct Model {
    state: State,
    cancel: Option<oneshot::Sender<()>>,
    pager: paging::Model,
}

pub enum State {
    Loading,
    Fetching,
    Loaded(logs::Resp),
}

impl Default for State {
    fn default() -> Self {
        Self::Loading
    }
}

#[derive(Clone, Debug)]
pub enum Msg {
    LogsFetched(fetch::ResponseDataResult<Response<logs::Resp>>),
    FetchOffset,
    Loop,
    Page(paging::Msg),
    Noop,
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::FetchOffset => {
            let builder = log::logs::Builder::new()
                .with_limit(model.pager.limit())
                .with_offset(model.pager.offset())
                .with_dir(SortDir::Desc);
            let query = builder.build();
            let req = fetch::Request::graphql_query(&query);

            orders.perform_cmd(req.fetch_json_data(Msg::LogsFetched));
        }
        Msg::LogsFetched(r) => {
            match r {
                Ok(Response::Data(d)) => {
                    orders
                        .proxy(Msg::Page)
                        .send_msg(paging::Msg::SetTotal(d.data.logs.meta.total_count as usize));

                    model.state = State::Loaded(d.data)
                }
                Ok(Response::Errors(e)) => {
                    error!("An error has occurred during fetching logs: ", e);
                }
                Err(fail_reason) => {
                    error!("An error has occurred: ", fail_reason);
                    orders.skip();
                }
            }

            orders.send_msg(Msg::Loop);
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

pub fn view(model: &Model, cache: &ArcCache) -> impl View<Msg> {
    div![match &model.state {
        State::Loading => loading::view(),
        State::Fetching => div![
            class![C.bg_menu_active],
            div![
                class![C.px_6, C.py_4, C.bg_blue_1000],
                div![class![C.font_medium, C.text_lg, C.text_gray_500], "Logs"],
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
        State::Loaded(response) => div![
            class![C.bg_menu_active],
            div![
                class![C.px_6, C.py_4, C.bg_blue_1000],
                div![class![C.font_medium, C.text_lg, C.text_gray_500], "Logs"],
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
            response.logs.data.iter().map(|x| { log_item_view(x, cache) })
        ],
    }]
}

fn log_severity<T>(x: LogSeverity) -> Node<T> {
    let cls = class![C.inline, C.w_4, C.h_4];

    match x {
        LogSeverity::Emergency => span![font_awesome(cls, "exclamation-circle").merge_attrs(class![C.text_red_500])],
        LogSeverity::Alert => span![font_awesome(cls, "exclamation-circle").merge_attrs(class![C.text_red_500])],
        LogSeverity::Critical => span![font_awesome(cls, "exclamation-circle").merge_attrs(class![C.text_red_500])],
        LogSeverity::Error => span![font_awesome(cls, "exclamation-triangle").merge_attrs(class![C.text_orange_500])],
        LogSeverity::Warning => span![font_awesome(cls, "exclamation-triangle").merge_attrs(class![C.text_yellow_500])],
        LogSeverity::Notice => span![font_awesome(cls, "info-circle").merge_attrs(class![C.text_blue_500])],
        LogSeverity::Informational => span![font_awesome(cls, "info-circle").merge_attrs(class![C.text_blue_500])],
        LogSeverity::Debug => span![font_awesome(cls, "info-circle").merge_attrs(class![C.text_gray_500])],
    }
}

fn log_item_view(log: &LogMessage, cache: &ArcCache) -> Node<Msg> {
    div![
        class![
            C.bg_menu,
            C.grid,
            C.grid_cols_4,
            C.gap_6,
            C.rounded,
            C.text_white,
            C.mx_4,
            C.my_6,
            C.p_8
        ],
        div![
            class![C.text_green_500, C.col_span_3],
            label_view("Time: "),
            &log.datetime.format("%H:%M:%S %Y/%m/%d").to_string()
        ],
        div![class![C.grid, C.justify_end], log_severity(log.severity)],
        div![class![C.col_span_4], log.message],
        div![
            class![C.col_span_2],
            label_view("FQDN: "),
            server_link(&log.fqdn, &cache.host)
        ],
        div![class![C.text_right, C.col_span_2], label_view("Service: "), log.tag],
    ]
}

fn server_link<T>(fqdn: &str, hosts: &im::HashMap<i32, Arc<Host>>) -> Node<T> {
    let x = hosts.values().find(|x| x.fqdn == fqdn);

    match x {
        Some(h) => a![
            class![C.text_blue_500, C.hover__underline],
            attrs! {At::Href => Route::Server(RouteId::from(h.id)).to_href()},
            fqdn
        ],
        None => plain![fqdn.to_string()],
    }
}

fn label_view<T>(s: &str) -> Node<T> {
    span![class![C.text_gray_500], s]
}
