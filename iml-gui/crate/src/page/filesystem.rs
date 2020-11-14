// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    components::{
        action_dropdown, alert_indicator, lock_indicator, paging, progress_circle, resource_links, stratagem,
        table as t, Placement,
    },
    extensions::MergeAttrs,
    generated::css_classes::C,
    get_target_from_managed_target,
    route::RouteId,
    sleep_with_handle, GMsg, Route,
};
use futures::channel::oneshot;
use iml_wire_types::{
    db::TargetRecord,
    warp_drive::{ArcCache, Locks},
    Filesystem, Session, Target, TargetConfParam, TargetKind, ToCompositeId,
};
use number_formatter as nf;
use seed::{prelude::*, *};
use std::{borrow::Cow, time::Duration};
use std::{collections::HashMap, sync::Arc};

pub struct Row {
    dropdown: action_dropdown::Model,
}

pub struct Model {
    pub fs: Arc<Filesystem>,
    mdts: Vec<Arc<Target<TargetConfParam>>>,
    mdt_paging: paging::Model,
    mgt: Vec<Arc<Target<TargetConfParam>>>,
    osts: Vec<Arc<Target<TargetConfParam>>>,
    ost_paging: paging::Model,
    rows: HashMap<i32, Row>,
    stratagem: stratagem::Model,
    stats: iml_influx::filesystem::Response,
    stats_cancel: Option<oneshot::Sender<()>>,
    stats_url: String,
}

impl Model {
    pub(crate) fn new(use_stratagem: bool, fs: &Arc<Filesystem>) -> Self {
        Self {
            fs: Arc::clone(fs),
            mdts: Default::default(),
            mdt_paging: Default::default(),
            mgt: Default::default(),
            osts: Default::default(),
            ost_paging: Default::default(),
            rows: Default::default(),
            stratagem: stratagem::Model::new(use_stratagem, Arc::clone(fs)),
            stats: iml_influx::filesystem::Response::default(),
            stats_cancel: None,
            stats_url: format!(r#"/influx?db=iml_stats&q={}"#, iml_influx::filesystem::query(&fs.name)),
        }
    }
}

#[derive(Clone, Debug)]
pub enum Msg {
    FetchStats,
    StatsFetched(Box<fetch::ResponseDataResult<iml_influx::filesystem::InfluxResponse>>),
    ActionDropdown(Box<action_dropdown::IdMsg>),
    AddTarget(Arc<Target<TargetConfParam>>),
    RemoveTarget(i32),
    SetTargets(Vec<Arc<Target<TargetConfParam>>>),
    OstPaging(paging::Msg),
    MdtPaging(paging::Msg),
    UpdatePaging,
    Stratagem(stratagem::Msg),
    Noop,
}

pub fn init(cache: &ArcCache, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    orders.send_msg(Msg::SetTargets(cache.target.values().cloned().collect()));

    stratagem::init(cache, &model.stratagem, &mut orders.proxy(Msg::Stratagem));

    orders.send_msg(Msg::FetchStats);
}

pub fn update(msg: Msg, cache: &ArcCache, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::FetchStats => {
            model.stats_cancel = None;
            let request = seed::fetch::Request::new(model.stats_url.clone());
            orders
                .skip()
                .perform_cmd(request.fetch_json_data(|x| Msg::StatsFetched(Box::new(x))));
        }
        Msg::StatsFetched(res) => {
            match *res {
                Ok(response) => {
                    model.stats = response.into();
                }
                Err(e) => {
                    error!(e);
                    orders.skip();
                }
            }
            let (cancel, fut) = sleep_with_handle(Duration::from_secs(30), Msg::FetchStats, Msg::Noop);
            model.stats_cancel = Some(cancel);
            orders.perform_cmd(fut);
        }
        Msg::ActionDropdown(x) => {
            let action_dropdown::IdMsg(id, msg) = *x;

            if let Some(x) = model.rows.get_mut(&id) {
                action_dropdown::update(
                    action_dropdown::IdMsg(id, msg),
                    cache,
                    &mut x.dropdown,
                    &mut orders.proxy(|x| Msg::ActionDropdown(Box::new(x))),
                );
            }
        }
        Msg::RemoveTarget(id) => {
            model.mgt.retain(|x| x.id != id);
            model.mdts.retain(|x| x.id != id);
            model.osts.retain(|x| x.id != id);

            model.rows.remove(&id);

            orders.send_msg(Msg::UpdatePaging);
        }
        Msg::AddTarget(x) => {
            if !is_fs_target(model.fs.id, &x) {
                return;
            }

            let xs = match x.kind {
                TargetKind::Mgt => &mut model.mgt,
                TargetKind::Mdt => &mut model.mdts,
                TargetKind::Ost => &mut model.osts,
            };

            match xs.iter().position(|y| y.id == x.id) {
                Some(p) => {
                    xs.remove(p);
                    xs.insert(p, x);
                }
                None => {
                    model.rows.insert(
                        x.id,
                        Row {
                            dropdown: action_dropdown::Model::new(vec![x.composite_id()]),
                        },
                    );
                }
            }

            orders.send_msg(Msg::UpdatePaging);
        }
        Msg::SetTargets(xs) => {
            model.rows = xs
                .iter()
                .map(|x| {
                    (
                        x.id,
                        Row {
                            dropdown: action_dropdown::Model::new(vec![x.composite_id()]),
                        },
                    )
                })
                .collect();

            let (mgt, mut mdts, mut osts) = xs.into_iter().filter(|t| is_fs_target(model.fs.id, t)).fold(
                (vec![], vec![], vec![]),
                |(mut mgt, mut mdts, mut osts), x| {
                    match x.kind {
                        TargetKind::Mgt => mgt.push(x),
                        TargetKind::Mdt => mdts.push(x),
                        TargetKind::Ost => osts.push(x),
                    }
                    (mgt, mdts, osts)
                },
            );

            mdts.sort_by(|a, b| natord::compare(&a.name, &b.name));
            osts.sort_by(|a, b| natord::compare(&a.name, &b.name));

            model.mgt = mgt;
            model.mdts = mdts;
            model.osts = osts;

            orders.send_msg(Msg::UpdatePaging);
        }
        Msg::MdtPaging(msg) => {
            paging::update(msg, &mut model.mdt_paging, &mut orders.proxy(Msg::MdtPaging));
        }
        Msg::OstPaging(msg) => {
            paging::update(msg, &mut model.ost_paging, &mut orders.proxy(Msg::OstPaging));
        }
        Msg::UpdatePaging => {
            orders
                .proxy(Msg::MdtPaging)
                .send_msg(paging::Msg::SetTotal(model.mdts.len()));
            orders
                .proxy(Msg::OstPaging)
                .send_msg(paging::Msg::SetTotal(model.osts.len()));
        }
        Msg::Stratagem(msg) => stratagem::update(msg, &mut model.stratagem, &mut orders.proxy(Msg::Stratagem)),
        Msg::Noop => {}
    }
}

fn paging_view(pager: &paging::Model) -> Node<paging::Msg> {
    div![
        class![C.flex, C.justify_end, C.py_1, C.pr_3],
        paging::limit_selection_view(pager),
        paging::page_count_view(pager),
        paging::next_prev_view(pager)
    ]
}

pub(crate) fn view(
    cache: &ArcCache,
    model: &Model,
    all_locks: &Locks,
    session: Option<&Session>,
    use_stratagem: bool,
) -> Node<Msg> {
    let stratagem_content = if use_stratagem {
        stratagem::view(&model.stratagem, all_locks).map_msg(Msg::Stratagem)
    } else {
        empty![]
    };

    div![
        details(cache, all_locks, model),
        stratagem_content,
        targets(
            "Management Target",
            cache,
            all_locks,
            session,
            &model.rows,
            &model.mgt[..],
            None
        ),
        targets(
            "Metadata Targets",
            cache,
            all_locks,
            session,
            &model.rows,
            &model.mdts[model.mdt_paging.range()],
            paging_view(&model.mdt_paging).map_msg(Msg::MdtPaging)
        ),
        targets(
            "Object Storage Targets",
            cache,
            all_locks,
            session,
            &model.rows,
            &model.osts[model.ost_paging.range()],
            paging_view(&model.ost_paging).map_msg(Msg::OstPaging)
        ),
    ]
}

fn details(cache: &ArcCache, all_locks: &Locks, model: &Model) -> Node<Msg> {
    let label_cls = class![C.col_span_2, C.p_4, C.self_center];
    let item_cls = class![
        C.bg_gray_100,
        C.col_span_10,
        C.grid,
        C.h_full
        C.items_center,
        C.p_2,
        C.self_center,
    ];

    div![
        class![C.bg_white, C.border_t, C.border_b, C.border, C.rounded_lg, C.shadow],
        div![
            class![C.flex, C.justify_between, C.px_6, C._mb_px, C.bg_gray_200],
            h3![
                class![C.py_4, C.font_normal, C.text_lg],
                format!("Filesystem {}", &model.fs.label)
            ]
        ],
        div![
            class![C.grid, C.grid_cols_12, C.gap_2, C.m_4],
            div![&label_cls, "Space Used / Available"],
            div![
                &item_cls,
                space_used_view(model.stats.bytes_free, model.stats.bytes_total, model.stats.bytes_avail)
            ],
            div![&label_cls, "Files Created / Available"],
            div![
                &item_cls,
                files_created_view(model.stats.files_free, model.stats.files_total)
            ],
            div![&label_cls, "State"],
            div![&item_cls, model.fs.state.to_string()],
            div![&label_cls, "MGS"],
            div![
                &item_cls,
                mgs(
                    cache,
                    &cache.target_record.values().cloned().collect::<Vec<_>>(),
                    &model.fs
                )
            ],
            div![&label_cls, "Number of MDTs"],
            div![&item_cls, model.mdts.len().to_string()],
            div![&label_cls, "Number of OSTs"],
            div![&item_cls, model.osts.len().to_string()],
            div![&label_cls, "Number of Connected Clients"],
            div![&item_cls, clients_view(model.stats.clients)],
            div![&label_cls, "Status"],
            div![&item_cls, status_view(cache, all_locks, &model.fs)],
            div![&label_cls, "Client mount command"],
            pre![
                class![C.break_all, C.text_white, C.whitespace_pre_line],
                &item_cls,
                style! {
                    St::BackgroundColor => "black"
                },
                model.fs.mount_command.to_string()
            ]
        ],
    ]
}

fn targets(
    title: &str,
    cache: &ArcCache,
    all_locks: &Locks,
    session: Option<&Session>,
    rows: &HashMap<i32, Row>,
    tgts: &[Arc<Target<TargetConfParam>>],
    pager: impl Into<Option<Node<Msg>>>,
) -> Node<Msg> {
    div![
        class![
            C.bg_white,
            C.border,
            C.border_b,
            C.border_t,
            C.mt_24,
            C.rounded_lg,
            C.shadow,
        ],
        div![
            class![C.flex, C.justify_between, C.px_6, C._mb_px, C.bg_gray_200],
            h3![class![C.py_4, C.font_normal, C.text_lg], title]
        ],
        table![
            class![C.table_auto, C.w_full],
            style! {
                St::BorderSpacing => px(10),
                St::BorderCollapse => "initial"
            },
            vec![
                t::thead_view(vec![
                    t::th_left(plain!["Name"]).merge_attrs(class![C.w_32]),
                    t::th_left(plain!["Device Path"]),
                    t::th_left(plain!["Active Server"]).merge_attrs(class![C.w_48, C.hidden, C.md__table_cell]),
                    t::th_left(plain!["Standby Servers"]).merge_attrs(class![C.w_48, C.hidden, C.md__table_cell]),
                    th![class![C.w_48]]
                ]),
                tbody![tgts
                    .iter()
                    .filter_map(|x| {
                        let t = get_target_from_managed_target(cache, x)?;

                        Some((x, t))
                    })
                    .map(move |(x, targ)| {
                        let dev_path = targ
                            .dev_path
                            .as_ref()
                            .map(|x| Cow::from(x.to_string()))
                            .unwrap_or_else(|| Cow::from("---"));

                        let active_host = targ.active_host_id.and_then(|x| cache.host.get(&x));

                        match rows.get(&x.id) {
                            None => empty![],
                            Some(row) => tr![
                                t::td_view(vec![
                                    a![
                                        class![C.text_blue_500, C.hover__underline],
                                        attrs! {At::Href => Route::Target(RouteId::from(x.id)).to_href()},
                                        &targ.name
                                    ],
                                    lock_indicator::view(all_locks, &x).merge_attrs(class![C.ml_2]),
                                    alert_indicator(&cache.active_alert, &x, true, Placement::Right)
                                        .merge_attrs(class![C.ml_2]),
                                ]),
                                t::td_view(plain![dev_path]),
                                t::td_view(resource_links::server_link(
                                    active_host.map(|x| &x.resource_uri),
                                    active_host.map(|x| x.fqdn.to_string()).as_deref().unwrap_or_default(),
                                ))
                                .merge_attrs(class![C.hidden, C.md__table_cell]),
                                t::td_view(standby_hosts_view(cache, &targ))
                                    .merge_attrs(class![C.hidden, C.md__table_cell]),
                                td![
                                    class![C.p_3, C.text_center],
                                    action_dropdown::view(x.id, &row.dropdown, all_locks, session)
                                        .map_msg(|x| Msg::ActionDropdown(Box::new(x)))
                                ]
                            ],
                        }
                    })]
            ]
        ]
        .merge_attrs(class![C.p_6]),
        match pager.into() {
            Some(x) => x,
            None => empty![],
        }
    ]
}

pub(crate) fn standby_hosts_view<T>(cache: &ArcCache, target: &TargetRecord) -> Node<T> {
    ul![target
        .host_ids
        .iter()
        .filter(|x| Some(**x) != target.active_host_id)
        .filter_map(|x| cache.host.get(&x))
        .map(|x| li![resource_links::server_link(Some(&x.resource_uri), &x.fqdn)])]
}

pub(crate) fn status_view<T>(cache: &ArcCache, all_locks: &Locks, x: &Filesystem) -> Node<T> {
    span![
        class![C.whitespace_no_wrap],
        span![class![C.mx_1], lock_indicator::view(all_locks, x)],
        alert_indicator(&cache.active_alert, x, false, Placement::Top)
    ]
}

pub(crate) fn mgs<T>(cache: &ArcCache, targets: &[Arc<TargetRecord>], f: &Filesystem) -> Node<T> {
    let x = targets
        .iter()
        .find(|t| t.get_kind() == TargetKind::Mgt && t.filesystems.contains(&f.name))
        .and_then(|x| x.active_host_id)
        .and_then(|x| cache.host.get(&x));

    if let Some(x) = x {
        resource_links::server_link(Some(&x.resource_uri), &x.fqdn)
    } else {
        plain!["---"]
    }
}

pub(crate) fn clients_view<T>(cc: impl Into<Option<u64>>) -> Node<T> {
    plain![cc.into().map(|c| c.to_string()).unwrap_or_else(|| "---".to_string())]
}

fn is_fs_target(fs_id: i32, t: &Target<TargetConfParam>) -> bool {
    t.filesystem_id == Some(fs_id)
        || t.filesystems
            .as_ref()
            .and_then(|f| f.iter().find(|x| x.id == fs_id))
            .is_some()
}

pub(crate) fn space_used_view<T>(
    free: impl Into<Option<u64>>,
    total: impl Into<Option<u64>>,
    avail: impl Into<Option<u64>>,
) -> Node<T> {
    total
        .into()
        .and_then(|total| {
            let free = free.into()?;
            let avail = avail.into()?;
            let used = total.saturating_sub(free) as f64;
            let pct = (used / (used as f64 + avail as f64) * 100.0f64).ceil();

            Some(span![
                class![C.whitespace_no_wrap],
                progress_circle::view((pct, progress_circle::used_to_color(pct)))
                    .merge_attrs(class![C.h_16, C.inline, C.mx_2]),
                nf::format_bytes(used as f64, None),
                " / ",
                nf::format_bytes(avail as f64, None)
            ])
        })
        .unwrap_or_else(|| plain!["---"])
}

fn files_created_view<T>(free: impl Into<Option<u64>>, total: impl Into<Option<u64>>) -> Node<T> {
    total
        .into()
        .and_then(|total| {
            let free = free.into()?;
            let used = total.saturating_sub(free) as f64;
            let pct = (used / total as f64) * 100.0f64;

            Some(span![
                class![C.whitespace_no_wrap],
                progress_circle::view((pct, progress_circle::used_to_color(pct)))
                    .merge_attrs(class![C.h_16, C.inline, C.mx_2]),
                nf::format_number(used as f64, None),
                " / ",
                nf::format_number(total as f64, None)
            ])
        })
        .unwrap_or_else(|| plain!["---"])
}
