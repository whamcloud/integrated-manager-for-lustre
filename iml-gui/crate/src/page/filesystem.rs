use crate::{
    components::{action_dropdown, alert_indicator, lock_indicator, pie_chart, table as T, Placement},
    extensions::MergeAttrs,
    extract_id,
    generated::css_classes::C,
    route::RouteId,
    GMsg, Route,
};
use iml_wire_types::{
    warp_drive::{ArcCache, ArcValuesExt, Locks},
    Filesystem, Target, TargetConfParam, TargetKind, ToCompositeId, VolumeOrResourceUri,
};
use number_formatter as NF;
use seed::{prelude::*, *};
use std::collections::{HashMap, HashSet};

pub struct Row {
    dropdown: action_dropdown::Model,
}

#[derive(Default)]
pub struct Model {
    pub id: u32,
    pub mdts: Vec<Target<TargetConfParam>>,
    pub mgt: Vec<Target<TargetConfParam>>,
    pub osts: Vec<Target<TargetConfParam>>,
    pub rows: HashMap<u32, Row>,
}

#[derive(Clone)]
pub enum Msg {
    ActionDropdown(Box<action_dropdown::IdMsg>),
    // AddTarget(Target<TargetConfParam>),
    // RemoveTarget(Target<TargetConfParam>),
    SetTargets(Vec<Target<TargetConfParam>>),
    WindowClick,
}

pub fn init(cache: &ArcCache, orders: &mut impl Orders<Msg, GMsg>) {
    orders.send_msg(Msg::SetTargets(cache.target.arc_values().cloned().collect()));
}

pub fn update(msg: Msg, cache: &ArcCache, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
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
        Msg::SetTargets(xs) => {
            let old_keys: HashSet<u32> = model.rows.keys().copied().collect();
            let new_keys: HashSet<u32> = xs.iter().map(|x| x.id).collect();

            let to_remove = &old_keys - &new_keys;
            let to_add = &new_keys - &old_keys;

            for x in to_remove {
                model.rows.remove(&x);
            }

            for x in to_add {
                let composite_id = xs.iter().find(|y| y.id == x).unwrap().composite_id();

                model.rows.insert(
                    x,
                    Row {
                        dropdown: action_dropdown::Model::new(vec![composite_id]),
                    },
                );
            }

            let (mgt, mut mdts, mut osts) = xs.into_iter().filter(|t| is_fs_target(model.id, t)).fold(
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
        }
        Msg::WindowClick => {
            for (_, r) in model.rows.iter_mut() {
                if r.dropdown.watching.should_update() {
                    r.dropdown.watching.update();
                }
            }
        }
    }
}

pub(crate) fn view(cache: &ArcCache, model: &Model, all_locks: &Locks) -> Node<Msg> {
    div![
        details_table(cache, all_locks, model),
        targets("Management Target", cache, all_locks, &model.rows, &model.mgt[..]),
        targets("Metadata Targets", cache, all_locks, &model.rows, &model.mdts[..]),
        targets("Object Storage Targets", cache, all_locks, &model.rows, &model.osts[..]),
    ]
}

fn details_table(cache: &ArcCache, all_locks: &Locks, model: &Model) -> Node<Msg> {
    let fs = cache.filesystem.get(&model.id).unwrap();

    div![
        class![C.bg_white, C.border_t, C.border_b, C.border, C.rounded_lg, C.shadow],
        div![
            class![C.flex, C.justify_between, C.px_6, C._mb_px, C.bg_gray_200],
            h3![
                class![C.py_4, C.font_normal, C.text_lg],
                format!("Filesystem {}", &fs.label)
            ]
        ],
        T::wrapper_view(vec![
            tr![T::th_left(plain!("Space Used / Total")), T::td_view(size_view(fs))],
            tr![
                T::th_left(plain!("Files Created / Maximum")),
                T::td_view(files_view(fs))
            ],
            tr![T::th_left(plain!("State")), T::td_view(plain![fs.state.to_string()])],
            tr![T::th_left(plain!("Management Server")), T::td_view(mgs(&model.mgt, fs)),],
            tr![
                T::th_left(plain!("Number of Metadata Targets")),
                T::td_view(plain!(model.mdts.len().to_string()))
            ],
            tr![
                T::th_left(plain!("Number of Object Storage Targets")),
                T::td_view(plain!(model.osts.len().to_string()))
            ],
            tr![
                T::th_left(plain!["Number of Connected Clients"]),
                T::td_view(clients_view(fs))
            ],
            tr![
                T::th_left(plain!["Status"]),
                T::td_view(status_view(cache, all_locks, &fs))
            ],
            tr![
                T::th_left(plain!["Client mount command"]),
                T::td_view(plain![fs.mount_command.to_string()])
            ],
        ])
    ]
}

fn targets(
    title: &str,
    cache: &ArcCache,
    all_locks: &Locks,
    rows: &HashMap<u32, Row>,
    tgts: &[Target<TargetConfParam>],
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
            class![C.table_fixed, C.w_full],
            style! {
                St::BorderSpacing => px(10),
                St::BorderCollapse => "initial"
            },
            vec![
                T::thead_view(vec![
                    T::th_left(plain!["Name"]).merge_attrs(class![C.w_32]),
                    T::th_left(plain!["Volume"]),
                    T::th_left(plain!["Primary Server"]).merge_attrs(class![C.w_48]),
                    T::th_left(plain!["Failover Server"]).merge_attrs(class![C.w_48]),
                    T::th_left(plain!["Started on"]).merge_attrs(class![C.w_48]),
                    th![class![C.w_48]]
                ]),
                tbody![tgts.iter().map(|x| match rows.get(&x.id) {
                    None => empty![],
                    Some(row) => tr![
                        T::td_view(vec![
                            a![
                                class![C.text_blue_500, C.hover__underline],
                                attrs! {At::Href => Route::Target(RouteId::from(x.id)).to_href()},
                                &x.name
                            ],
                            lock_indicator::view(&all_locks, &x),
                            alert_indicator(&cache.active_alert, &x, true, Placement::Top),
                        ]),
                        T::td_view(volume_link(x)),
                        T::td_view(server_link(Some(&x.primary_server), &x.primary_server_name)),
                        T::td_view(server_link(x.failover_servers.first(), &x.failover_server_name)),
                        T::td_view(server_link(x.active_host.as_ref(), &x.active_host_name)),
                        td![
                            class![C.p_3, C.text_center],
                            action_dropdown::view(x.id, &row.dropdown, all_locks)
                                .map_msg(|x| Msg::ActionDropdown(Box::new(x)))
                        ]
                    ],
                })]
            ]
        ]
    ]
}

pub(crate) fn status_view<T>(cache: &ArcCache, all_locks: &Locks, x: &Filesystem) -> Node<T> {
    span![
        class![C.whitespace_no_wrap],
        span![class![C.mx_1], lock_indicator::view(&all_locks, x)],
        alert_indicator(&cache.active_alert, x, false, Placement::Top)
    ]
}

pub(crate) fn mgs<T>(xs: &Vec<Target<TargetConfParam>>, f: &Filesystem) -> Node<T> {
    if let Some(t) = xs.iter().find(|t| t.kind == TargetKind::Mgt && f.mgt == t.resource_uri) {
        server_link(Some(&t.primary_server), &t.primary_server_name)
    } else {
        plain!("N/A")
    }
}

pub(crate) fn clients_view<I>(f: &Filesystem) -> Node<I> {
    plain!(match f.client_count {
        Some(c) => c.round().to_string(),
        None => "N/A".to_string(),
    })
}

pub(crate) fn size_view<I>(f: &Filesystem) -> Node<I> {
    if let Some((u, t)) = f.bytes_total.and_then(|t| f.bytes_free.map(|f| (t - f, t))) {
        span![
            class![C.whitespace_no_wrap],
            pie_chart(u / t).merge_attrs(class![C.h_8, C.inline, C.mx_2]),
            NF::format_bytes(u, None),
            " / ",
            NF::format_bytes(t, None)
        ]
    } else {
        plain!("N/A")
    }
}

fn files_view<I>(fs: &Filesystem) -> Node<I> {
    if let Some((u, t)) = fs.files_total.and_then(|t| fs.files_free.map(|f| (t - f, t))) {
        log!("used: {}, total: {}", u, t);
        span![
            class![C.whitespace_no_wrap],
            pie_chart(u / t).merge_attrs(class![C.h_8, C.inline, C.mx_2]),
            NF::format_number(u, None),
            " / ",
            NF::format_number(t, None)
        ]
    } else {
        plain!("N/A")
    }
}

fn is_fs_target(fs_id: u32, t: &Target<TargetConfParam>) -> bool {
    t.filesystem_id == Some(fs_id)
        || t.filesystems
            .as_ref()
            .and_then(|f| f.iter().find(|x| x.id == fs_id))
            .is_some()
}

fn server_link<I>(uri: Option<&String>, txt: &str) -> Node<I> {
    if let Some(u) = uri {
        let srv_id = extract_id(u).unwrap();
        a![
            class![C.text_blue_500, C.hover__underline, C.block],
            attrs! {At::Href => Route::Server(RouteId::from(srv_id)).to_href()},
            txt
        ]
    } else {
        plain!("N/A")
    }
}

fn volume_link<I>(t: &Target<TargetConfParam>) -> Node<I> {
    let vol_id = match &t.volume {
        VolumeOrResourceUri::ResourceUri(url) => extract_id(url).unwrap().parse::<u32>().unwrap(),
        VolumeOrResourceUri::Volume(v) => v.id,
    };

    a![
        class![C.text_blue_500, C.hover__underline, C.break_all],
        attrs! {At::Href => Route::Volume(RouteId::from(vol_id)).to_href()},
        t.volume_name,
    ]
}
