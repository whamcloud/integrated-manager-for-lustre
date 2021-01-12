// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use super::*;
use crate::{extensions::RequestExt, font_awesome};
use chrono_humanize::{Accuracy, HumanTime, Tense};
use emf_wire_types::snapshot::SnapshotInterval;
use std::time::Duration;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SortField {
    FilesystemName,
    Interval,
}

impl Default for SortField {
    fn default() -> Self {
        Self::FilesystemName
    }
}

#[derive(Clone, Debug)]
pub enum Msg {
    Page(paging::Msg),
    Sort,
    Delete(Arc<SnapshotInterval>),
    SnapshotDeleteIntervalResp(fetch::ResponseDataResult<Response<snapshot::remove_interval::Resp>>),
    SortBy(table::SortBy<SortField>),
}

#[derive(Default, Debug)]
pub struct Model {
    pager: paging::Model,
    rows: Vec<Arc<SnapshotInterval>>,
    sort: (SortField, paging::Dir),
    take: take::Model,
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::SortBy(table::SortBy(x)) => {
            let dir = if x == model.sort.0 {
                model.sort.1.next()
            } else {
                paging::Dir::default()
            };

            model.sort = (x, dir);

            orders.send_msg(Msg::Sort);
        }
        Msg::Page(msg) => {
            paging::update(msg, &mut model.pager, &mut orders.proxy(Msg::Page));
        }
        Msg::Sort => {
            let sort_fn = match model.sort {
                (SortField::FilesystemName, paging::Dir::Asc) => {
                    Box::new(|a: &Arc<SnapshotInterval>, b: &Arc<SnapshotInterval>| {
                        natord::compare(&a.filesystem_name, &b.filesystem_name)
                    }) as Box<dyn FnMut(&Arc<SnapshotInterval>, &Arc<SnapshotInterval>) -> Ordering>
                }
                (SortField::FilesystemName, paging::Dir::Desc) => {
                    Box::new(|a: &Arc<SnapshotInterval>, b: &Arc<SnapshotInterval>| {
                        natord::compare(&b.filesystem_name, &a.filesystem_name)
                    })
                }
                (SortField::Interval, paging::Dir::Asc) => {
                    Box::new(|a: &Arc<SnapshotInterval>, b: &Arc<SnapshotInterval>| {
                        a.interval.0.partial_cmp(&b.interval.0).unwrap()
                    })
                }
                (SortField::Interval, paging::Dir::Desc) => {
                    Box::new(|a: &Arc<SnapshotInterval>, b: &Arc<SnapshotInterval>| {
                        b.interval.0.partial_cmp(&a.interval.0).unwrap()
                    })
                }
            };

            model.rows.sort_by(sort_fn);
        }
        Msg::Delete(x) => {
            if let Ok(true) = window().confirm_with_message("Are you sure you want to delete this interval?") {
                let query = snapshot::remove_interval::build(x.id);

                let req = fetch::Request::graphql_query(&query);

                orders.perform_cmd(req.fetch_json_data(|x| Msg::SnapshotDeleteIntervalResp(x)));
            }
        }
        Msg::SnapshotDeleteIntervalResp(x) => match x {
            Ok(Response::Data(_)) => {}
            Ok(Response::Errors(e)) => {
                error!("An error has occurred during Snapshot deletion: ", e);
            }
            Err(e) => {
                error!("An error has occurred during Snapshot deletion: ", e);
            }
        },
    };
}

impl RecordChange<Msg> for Model {
    fn update_record(&mut self, _: ArcRecord, cache: &ArcCache, orders: &mut impl Orders<Msg, GMsg>) {
        self.rows = cache.snapshot_interval.values().cloned().collect();

        orders.proxy(Msg::Page).send_msg(paging::Msg::SetTotal(self.rows.len()));

        orders.send_msg(Msg::Sort);
    }
    fn remove_record(&mut self, _: RecordId, cache: &ArcCache, orders: &mut impl Orders<Msg, GMsg>) {
        self.rows = cache.snapshot_interval.values().cloned().collect();

        orders.proxy(Msg::Page).send_msg(paging::Msg::SetTotal(self.rows.len()));

        orders.send_msg(Msg::Sort);
    }
    fn set_records(&mut self, cache: &ArcCache, orders: &mut impl Orders<Msg, GMsg>) {
        self.rows = cache.snapshot_interval.values().cloned().collect();

        orders.proxy(Msg::Page).send_msg(paging::Msg::SetTotal(self.rows.len()));

        orders.send_msg(Msg::Sort);
    }
}

pub fn view(model: &Model, cache: &ArcCache, session: Option<&Session>) -> Node<Msg> {
    panel::view(
        h3![class![C.py_4, C.font_normal, C.text_lg], "Automated Snapshot Rules"],
        div![
            table::wrapper_view(vec![
                table::thead_view(vec![
                    table::sort_header("FS Name", SortField::FilesystemName, model.sort.0, model.sort.1)
                        .map_msg(Msg::SortBy),
                    table::sort_header("Interval", SortField::Interval, model.sort.0, model.sort.1)
                        .map_msg(Msg::SortBy),
                    table::th_view(plain!["Use Barrier"]),
                    table::th_view(plain!["Last Run"]),
                    restrict::view(session, GroupType::FilesystemAdministrators, th![]),
                ]),
                tbody![model.rows[model.pager.range()].iter().map(|x| {
                    tr![
                        td![
                            table::td_cls(),
                            class![C.text_center],
                            match get_fs_by_name(cache, &x.filesystem_name) {
                                Some(x) => {
                                    div![resource_links::fs_link(&x)]
                                }
                                None => {
                                    plain![x.filesystem_name.to_string()]
                                }
                            }
                        ],
                        table::td_center(plain![display_interval(x.interval.0)]),
                        table::td_center(plain![match x.use_barrier {
                            true => {
                                "yes"
                            }
                            false => {
                                "no"
                            }
                        }]),
                        table::td_center(plain![x
                            .last_run
                            .map(|x| x.format("%m/%d/%Y %H:%M:%S").to_string())
                            .unwrap_or_else(|| "---".to_string())]),
                        td![
                            class![C.flex, C.justify_center, C.p_4, C.px_3],
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
                                    font_awesome(class![C.w_3, C.h_3, C.inline, C.mr_1], "trash"),
                                    "Delete Rule",
                                    simple_ev(Ev::Click, Msg::Delete(Arc::clone(&x)))
                                ]
                            )
                        ]
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

fn display_interval(x: Duration) -> String {
    chrono::Duration::from_std(x)
        .map(HumanTime::from)
        .map(|x| x.to_text_en(Accuracy::Precise, Tense::Present))
        .unwrap_or("---".into())
}
