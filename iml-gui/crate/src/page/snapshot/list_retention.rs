// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use super::*;
use crate::{extensions::RequestExt, font_awesome};
use iml_wire_types::snapshot::{ReserveUnit, SnapshotRetention};

#[derive(Clone, Debug)]
pub enum Msg {
    Page(paging::Msg),
    Delete(Arc<SnapshotRetention>),
    DeleteRetentionResp(fetch::ResponseDataResult<Response<snapshot::remove_retention::Resp>>),
}

#[derive(Default, Debug)]
pub struct Model {
    pager: paging::Model,
    rows: Vec<Arc<SnapshotRetention>>,
    take: take::Model,
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::Page(msg) => {
            paging::update(msg, &mut model.pager, &mut orders.proxy(Msg::Page));
        }
        Msg::Delete(x) => {
            if let Ok(true) = window().confirm_with_message("Are you sure you want to delete this retention policy?") {
                let query = snapshot::remove_retention::build(x.id);

                let req = fetch::Request::graphql_query(&query);

                orders.perform_cmd(req.fetch_json_data(Msg::DeleteRetentionResp));
            }
        }
        Msg::DeleteRetentionResp(x) => match x {
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
        self.rows = cache.snapshot_retention.values().cloned().collect();

        orders.proxy(Msg::Page).send_msg(paging::Msg::SetTotal(self.rows.len()));
    }
    fn remove_record(&mut self, _: RecordId, cache: &ArcCache, orders: &mut impl Orders<Msg, GMsg>) {
        self.rows = cache.snapshot_retention.values().cloned().collect();

        orders.proxy(Msg::Page).send_msg(paging::Msg::SetTotal(self.rows.len()));
    }
    fn set_records(&mut self, cache: &ArcCache, orders: &mut impl Orders<Msg, GMsg>) {
        self.rows = cache.snapshot_retention.values().cloned().collect();

        orders.proxy(Msg::Page).send_msg(paging::Msg::SetTotal(self.rows.len()));
    }
}

pub fn view(model: &Model, cache: &ArcCache, session: Option<&Session>) -> Node<Msg> {
    panel::view(
        h3![class![C.py_4, C.font_normal, C.text_lg], "Snapshot Retention Policies"],
        div![
            table::wrapper_view(vec![
                table::thead_view(vec![
                    table::th_view(plain!["Filesystem"]),
                    table::th_view(plain!["Reserve"]),
                    table::th_view(plain!["Keep"]),
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
                        table::td_center(plain![format!(
                            "{} {}",
                            x.reserve_value,
                            match x.reserve_unit {
                                ReserveUnit::Percent => "%",
                                ReserveUnit::Gibibytes => "GiB",
                                ReserveUnit::Tebibytes => "TiB",
                            }
                        )]),
                        table::td_center(plain![x.keep_num.to_string()]),
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
                                    "Delete Policy",
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
