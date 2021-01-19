// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.
use crate::{
    components::{font_awesome, paging, panel, restrict, table},
    extensions::MergeAttrs as _,
    generated::css_classes::C,
    sleep_with_handle, GMsg, RequestExt,
};
use emf_graphql_queries::{stratagem, Response};
use emf_wire_types::{GroupType, Session, StratagemReport};
use futures::channel::oneshot;
use number_formatter::format_bytes;
use seed::{prelude::*, *};
use std::{cmp::Ordering, time::Duration};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SortField {
    ModifyTime,
    Size,
    Filename,
}

impl Default for SortField {
    fn default() -> Self {
        Self::ModifyTime
    }
}

#[derive(Default, Debug)]
pub struct Model {
    pager: paging::Model,
    rows: Vec<StratagemReport>,
    sort: (SortField, paging::Dir),
    cancel: Option<oneshot::Sender<()>>,
}

#[derive(Clone, Debug)]
pub enum Msg {
    FetchReports,
    Reports(fetch::ResponseDataResult<Response<stratagem::list_reports::Resp>>),
    Page(paging::Msg),
    Sort,
    SortBy(table::SortBy<SortField>),
    DeleteReport(String),
    ReportDeleted(fetch::ResponseDataResult<Response<stratagem::delete_report::Resp>>),
    Noop,
}

pub fn view(model: &Model, session: Option<&Session>) -> Node<Msg> {
    if model.rows.is_empty() {
        return empty![];
    }

    panel::view(
        h3![class![C.py_4, C.font_normal, C.text_lg], "Stratagem Reports"],
        div![
            table::wrapper_view(vec![
                table::thead_view(vec![
                    table::sort_header("Filename", SortField::Filename, model.sort.0, model.sort.1)
                        .map_msg(Msg::SortBy),
                    table::sort_header("Size", SortField::Size, model.sort.0, model.sort.1).map_msg(Msg::SortBy),
                    table::sort_header("Modify Time", SortField::ModifyTime, model.sort.0, model.sort.1)
                        .map_msg(Msg::SortBy),
                    restrict::view(session, GroupType::FilesystemAdministrators, th![]),
                ]),
                tbody![model.rows[model.pager.range()].iter().map(|x| {
                    tr![
                        td![
                            table::td_cls(),
                            a![
                                class![C.text_blue_500, C.hover__underline],
                                attrs! {
                                At::Download => x.filename,
                                At::Href => format!("/api/report/{}", x.filename)},
                                x.filename
                            ]
                        ],
                        table::td_center(plain![format_bytes(x.size as f64, 0)]),
                        table::td_center(plain![x.modify_time.format("%m/%d/%Y %H:%M:%S").to_string()]),
                        restrict::view(
                            session,
                            GroupType::FilesystemAdministrators,
                            button![
                                class![
                                    C.bg_blue_500,
                                    C.duration_300,
                                    C.flex,
                                    C.hover__bg_blue_400,
                                    C.items_center,
                                    C.px_6,
                                    C.py_2,
                                    C.rounded_sm,
                                    C.text_white,
                                    C.transition_colors,
                                ],
                                font_awesome(class![C.w_3, C.h_3, C.inline, C.mr_2], "trash"),
                                "Delete File",
                                simple_ev(Ev::Click, Msg::DeleteReport(x.filename.clone()))
                            ]
                        )
                    ]
                })]
            ])
            .merge_attrs(class![C.my_6]),
            div![
                class![C.flex, C.justify_end, C.py_1, C.pr_3],
                paging::limit_selection_view(&model.pager).map_msg(Msg::Page),
                paging::page_count_view(&model.pager),
                paging::next_prev_view(&model.pager).map_msg(Msg::Page)
            ]
        ],
    )
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::Page(m) => {
            paging::update(m, &mut model.pager, &mut orders.proxy(Msg::Page));
        }
        Msg::FetchReports => {
            model.cancel = None;
            let query = stratagem::list_reports::build();
            let req = fetch::Request::graphql_query(&query);

            orders.perform_cmd(req.fetch_json_data(Msg::Reports));
        }
        Msg::Reports(x) => {
            match x {
                Ok(Response::Data(d)) => {
                    model.rows = d.data.stratagem.stratagem_reports;
                    orders
                        .proxy(Msg::Page)
                        .send_msg(paging::Msg::SetTotal(model.rows.len()));
                    orders.send_msg(Msg::Sort);
                }
                Ok(Response::Errors(e)) => {
                    error!("Stratagem reports were not fetched: ", e);
                }
                Err(e) => {
                    error!("Stratagem reports were not fetched: ", e);
                }
            }
            let (cancel, fut) = sleep_with_handle(Duration::from_secs(30), Msg::FetchReports, Msg::Noop);
            model.cancel = Some(cancel);
            orders.perform_cmd(fut);
        }
        Msg::DeleteReport(filename) => {
            if let Ok(true) = window().confirm_with_message(&format!("Delete {}?", filename)) {
                let query = stratagem::delete_report::build(filename);
                let req = fetch::Request::graphql_query(&query);

                orders.perform_cmd(req.fetch_json_data(Msg::ReportDeleted));
            }
        }
        Msg::ReportDeleted(x) => {
            match x {
                Ok(Response::Data(_)) => {}
                Ok(Response::Errors(e)) => {
                    error!("Error deleting the report: ", e);
                }
                Err(e) => {
                    error!("Error deleting the report: ", e);
                }
            }
            orders.send_msg(Msg::FetchReports);
        }
        Msg::SortBy(table::SortBy(x)) => {
            let dir = if x == model.sort.0 {
                model.sort.1.next()
            } else {
                paging::Dir::default()
            };

            model.sort = (x, dir);

            orders.send_msg(Msg::Sort);
        }
        Msg::Sort => {
            let sort_fn = match model.sort.0 {
                SortField::Filename => {
                    |a: &StratagemReport, b: &StratagemReport| natord::compare(&a.filename, &b.filename)
                }
                SortField::Size => |a: &StratagemReport, b: &StratagemReport| a.size.cmp(&b.size),
                SortField::ModifyTime => |a: &StratagemReport, b: &StratagemReport| a.modify_time.cmp(&b.modify_time),
            };

            let sort_dir_fn = if paging::Dir::Desc == model.sort.1 {
                Box::new(|a: &StratagemReport, b: &StratagemReport| sort_fn(b, a))
                    as Box<dyn FnMut(&StratagemReport, &StratagemReport) -> Ordering>
            } else {
                Box::new(|a: &StratagemReport, b: &StratagemReport| sort_fn(a, b))
            };

            model.rows.sort_by(sort_dir_fn);
        }
        Msg::Noop => {}
    }
}

pub fn init(model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    model.sort.1 = paging::Dir::Desc;
    orders.send_msg(Msg::FetchReports);
}
