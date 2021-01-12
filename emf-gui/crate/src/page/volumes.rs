// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    components::{paging, panel, resource_links, table},
    extensions::MergeAttrs as _,
    generated::css_classes::C,
    page::RecordChange,
    route::{Route, RouteId},
    GMsg,
};
use emf_wire_types::{
    db::{VolumeNodeRecord, VolumeRecord},
    warp_drive::{ArcCache, ArcRecord, RecordId},
    Host,
};
use seed::{prelude::*, *};
use std::{cmp::Ordering, sync::Arc};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SortField {
    Path,
    Size,
}

impl Default for SortField {
    fn default() -> Self {
        Self::Path
    }
}

type Row = (Arc<VolumeRecord>, Vec<Arc<VolumeNodeRecord>>, Vec<Arc<Host>>);

#[derive(Default)]
pub struct Model {
    pub(crate) host: Option<Arc<Host>>,
    pager: paging::Model,
    sort: (SortField, paging::Dir),
    rows: Vec<Row>,
}

impl RecordChange<Msg> for Model {
    fn update_record(&mut self, record: ArcRecord, cache: &ArcCache, orders: &mut impl Orders<Msg, GMsg>) {
        match record {
            ArcRecord::Volume(_) | ArcRecord::VolumeNode(_) | ArcRecord::Host(_) => {
                self.rows = build_rows(cache, &self.host);

                orders.proxy(Msg::Page).send_msg(paging::Msg::SetTotal(self.rows.len()));

                orders.send_msg(Msg::Sort);
            }
            _ => {}
        }
    }
    fn remove_record(&mut self, id: RecordId, cache: &ArcCache, orders: &mut impl Orders<Msg, GMsg>) {
        match id {
            RecordId::Volume(_) | RecordId::VolumeNode(_) | RecordId::Host(_) => {
                self.rows = build_rows(cache, &self.host);

                orders.proxy(Msg::Page).send_msg(paging::Msg::SetTotal(self.rows.len()));

                orders.send_msg(Msg::Sort);
            }
            _ => {}
        }
    }
    fn set_records(&mut self, cache: &ArcCache, orders: &mut impl Orders<Msg, GMsg>) {
        self.rows = build_rows(cache, &self.host);

        orders.proxy(Msg::Page).send_msg(paging::Msg::SetTotal(self.rows.len()));

        orders.send_msg(Msg::Sort);
    }
}

impl From<&Arc<Host>> for Model {
    fn from(host: &Arc<Host>) -> Self {
        Self {
            host: Some(Arc::clone(host)),
            ..Default::default()
        }
    }
}

fn build_rows(cache: &ArcCache, host: &Option<Arc<Host>>) -> Vec<Row> {
    let x: im::HashMap<i32, Vec<_>> = cache.volume_node.values().fold(im::hashmap! {}, |mut acc, x| {
        acc.entry(x.volume_id)
            .and_modify(|xs| {
                xs.push(Arc::clone(x));
            })
            .or_insert_with(|| vec![Arc::clone(x)]);

        acc
    });

    x.into_iter()
        .filter_map(|(vid, xs)| {
            let v = cache.volume.get(&vid)?;

            let hs = xs
                .iter()
                .filter_map(|x| cache.host.get(&x.host_id))
                .map(|x| Arc::clone(x))
                .collect();

            Some((Arc::clone(v), xs, hs))
        })
        .filter(|(_, _, hs): &Row| hs.iter().any(|h| host.as_ref().map(|h0| h0.id == h.id).unwrap_or(true)))
        .collect()
}

pub fn init(cache: &ArcCache, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    model.set_records(cache, orders);
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
        Msg::Sort => {
            let sort_fn = match model.sort {
                (SortField::Path, paging::Dir::Asc) => {
                    Box::new(|a: &Row, b: &Row| natord::compare(&a.1[0].path, &b.1[0].path))
                        as Box<dyn FnMut(&Row, &Row) -> Ordering>
                }
                (SortField::Path, paging::Dir::Desc) => {
                    Box::new(|a: &Row, b: &Row| natord::compare(&b.1[0].path, &a.1[0].path))
                }
                (SortField::Size, paging::Dir::Asc) => {
                    Box::new(|a: &Row, b: &Row| a.0.size.partial_cmp(&b.0.size).unwrap())
                }
                (SortField::Size, paging::Dir::Desc) => {
                    Box::new(|a: &Row, b: &Row| b.0.size.partial_cmp(&a.0.size).unwrap())
                }
            };

            model.rows.sort_by(sort_fn);
        }
        Msg::Page(msg) => {
            paging::update(msg, &mut model.pager, &mut orders.proxy(Msg::Page));
        }
    }
}

pub fn view(model: &Model) -> impl View<Msg> {
    panel::view(
        h3![class![C.py_4, C.font_normal, C.text_lg], "Volumes"],
        div![
            table::wrapper_view(vec![
                table::thead_view(vec![
                    table::sort_header("Path", SortField::Path, model.sort.0, model.sort.1).map_msg(Msg::SortBy),
                    table::sort_header("Size", SortField::Size, model.sort.0, model.sort.1).map_msg(Msg::SortBy),
                    table::th_view(plain!["Hosts"]),
                ]),
                tbody![model.rows[model.pager.range()].iter().map(|(v, vns, hs)| {
                    tr![
                        table::td_center(resource_links::label_view(
                            &vns[0].path,
                            Route::Volume(RouteId::from(v.id))
                        )),
                        table::td_center(plain![match v.size {
                            Some(x) => number_formatter::format_bytes(x as f64, None),
                            None => "---".into(),
                        }]),
                        table::td_center(
                            hs.iter()
                                .map(|h| {
                                    div![resource_links::href_view(&h.fqdn, Route::Server(RouteId::from(h.id)))]
                                })
                                .collect::<Vec<_>>()
                        )
                    ]
                })],
            ])
            .merge_attrs(class![C.my_6]),
            div![
                class![C.flex, C.justify_end, C.py_1, C.pr_3],
                paging::limit_selection_view(&model.pager).map_msg(Msg::Page),
                paging::page_count_view(&model.pager),
                paging::next_prev_view(&model.pager).map_msg(Msg::Page)
            ],
        ],
    )
}
