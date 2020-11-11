// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use super::*;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SortField {
    CreationTime,
    Name,
}

impl Default for SortField {
    fn default() -> Self {
        Self::CreationTime
    }
}

#[derive(Default, Debug)]
pub struct Model {
    pager: paging::Model,
    rows: Vec<Arc<SnapshotRecord>>,
    sort: (SortField, paging::Dir),
}

impl RecordChange<Msg> for Model {
    fn update_record(&mut self, _: ArcRecord, cache: &ArcCache, orders: &mut impl Orders<Msg, GMsg>) {
        self.rows = cache.snapshot.values().cloned().collect();

        orders.proxy(Msg::Page).send_msg(paging::Msg::SetTotal(self.rows.len()));

        orders.send_msg(Msg::Sort);
    }
    fn remove_record(&mut self, _: RecordId, cache: &ArcCache, orders: &mut impl Orders<Msg, GMsg>) {
        self.rows = cache.snapshot.values().cloned().collect();

        orders.proxy(Msg::Page).send_msg(paging::Msg::SetTotal(self.rows.len()));

        orders.send_msg(Msg::Sort);
    }
    fn set_records(&mut self, cache: &ArcCache, orders: &mut impl Orders<Msg, GMsg>) {
        self.rows = cache.snapshot.values().cloned().collect();

        orders.proxy(Msg::Page).send_msg(paging::Msg::SetTotal(self.rows.len()));

        orders.send_msg(Msg::Sort);
    }
}

#[derive(Clone, Debug)]
pub enum Msg {
    Page(paging::Msg),
    Sort,
    SortBy(table::SortBy<SortField>),
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
                (SortField::Name, paging::Dir::Asc) => Box::new(|a: &Arc<SnapshotRecord>, b: &Arc<SnapshotRecord>| {
                    natord::compare(&a.snapshot_name, &b.snapshot_name)
                })
                    as Box<dyn FnMut(&Arc<SnapshotRecord>, &Arc<SnapshotRecord>) -> Ordering>,
                (SortField::Name, paging::Dir::Desc) => Box::new(|a: &Arc<SnapshotRecord>, b: &Arc<SnapshotRecord>| {
                    natord::compare(&b.snapshot_name, &a.snapshot_name)
                }),
                (SortField::CreationTime, paging::Dir::Asc) => {
                    Box::new(|a: &Arc<SnapshotRecord>, b: &Arc<SnapshotRecord>| {
                        a.create_time.partial_cmp(&b.create_time).unwrap()
                    })
                }
                (SortField::CreationTime, paging::Dir::Desc) => {
                    Box::new(|a: &Arc<SnapshotRecord>, b: &Arc<SnapshotRecord>| {
                        b.create_time.partial_cmp(&a.create_time).unwrap()
                    })
                }
            };

            model.rows.sort_by(sort_fn);
        }
    }
}

pub fn view(model: &Model, cache: &ArcCache) -> Node<Msg> {
    if model.rows.is_empty() {
        return empty!();
    }

    panel::view(
        h3![class![C.py_4, C.font_normal, C.text_lg], "Snapshots"],
        div![
            table::wrapper_view(vec![
                table::thead_view(vec![
                    table::sort_header("Name", SortField::Name, model.sort.0, model.sort.1).map_msg(Msg::SortBy),
                    table::th_view(plain!["FS Name"]),
                    table::sort_header("Creation Time", SortField::CreationTime, model.sort.0, model.sort.1)
                        .map_msg(Msg::SortBy),
                    table::th_view(plain!["Comment"]),
                    table::th_view(plain!["State"]),
                ]),
                tbody![model.rows[model.pager.range()].iter().map(|x| {
                    tr![
                        td![table::td_cls(), class![C.text_center], &x.snapshot_name],
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
                        table::td_center(plain![x.create_time.format("%m/%d/%Y %H:%M:%S").to_string()]),
                        td![
                            table::td_cls(),
                            class![C.text_center],
                            x.comment.as_deref().unwrap_or("---")
                        ],
                        table::td_center(plain![match &x.mounted {
                            true => "mounted",
                            false => "unmounted",
                        }]),
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
