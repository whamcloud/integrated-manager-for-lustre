use crate::{
    components::{alert_indicator, lock_indicator, pie_chart, table as T, Placement},
    extensions::MergeAttrs,
    extract_id,
    generated::css_classes::C,
    route::RouteId,
    Model, Route,
};
use im::HashMap;
use iml_wire_types::{
    warp_drive::{ArcCache, ArcValuesExt},
    Filesystem, ResourceUri, Target, TargetConfParam, TargetKind, ToCompositeId, VolumeOrResourceUri,
};
use number_formatter as NF;
use seed::{prelude::*, *};
use std::sync::Arc;

pub(crate) fn view<I>(model: &Model, f: &Filesystem) -> Node<I> {
    let (mgt, mut mdt, mut ost) = model.records.target.values().filter(|t| is_fs_target(f, t)).fold(
        (vec![], vec![], vec![]),
        |(mut mgt, mut mdt, mut ost), t| {
            match t.kind {
                TargetKind::Mgt => mgt.push(t),
                TargetKind::Mdt => mdt.push(t),
                TargetKind::Ost => ost.push(t),
            }
            (mgt, mdt, ost)
        },
    );

    mdt.sort_by(|a, b| natord::compare(&a.name, &b.name));
    ost.sort_by(|a, b| natord::compare(&a.name, &b.name));

    div![
        details_table(model, f),
        T::wrapper_view(vec![
            targets("Management Target", model, &mgt[..]),
            targets("Metadata Targets", model, &mdt[..]),
            targets("Object Storage Targets", model, &ost[..]),
        ])
    ]
}

fn details_table<I>(model: &Model, f: &Filesystem) -> Node<I> {
    div![
        class![C.bg_white, C.border_t, C.border_b, C.border, C.rounded_lg, C.shadow],
        div![
            class![C.flex, C.justify_between, C.px_6, C._mb_px, C.bg_gray_200],
            h3![
                class![C.py_4, C.font_normal, C.text_lg],
                format!("File system {}", f.label)
            ]
        ],
        T::wrapper_view(vec![
            tr![T::th_right(plain!("Space Used / Total")), T::td_view(size_view(f))],
            tr![
                T::th_right(plain!("Files Created / Maximum")),
                T::td_view(files_view(f))
            ],
            tr![T::th_right(plain!("State")), T::td_view(plain!(f.state.clone()))],
            tr![
                T::th_right(plain!("Management Server")),
                T::td_view(mgs(&model.records.target, f)),
            ],
            tr![
                T::th_right(plain!("Number of Metadata Targets")),
                T::td_view(plain!(f.mdts.len().to_string()))
            ],
            tr![
                T::th_right(plain!("Number of Object Storage Targets")),
                T::td_view(plain!(f.osts.len().to_string()))
            ],
            tr![
                T::th_right(plain!("Number of Connected Clients")),
                T::td_view(clients_view(f))
            ],
            tr![T::th_right(plain!("Status")), T::td_view(status_view(model, f))],
            tr![
                T::th_right(plain!("Client mount command")),
                T::td_view(plain!(f.mount_command.clone()))
            ],
        ])
    ]
}

fn targets<I>(caption: &str, model: &Model, tgts: &[&Arc<Target<TargetConfParam>>]) -> Node<I> {
    div![
        class![
            C.bg_white,
            C.border,
            C.border_b,
            C.border_t,
            C.mt_4
            C.rounded_lg,
            C.shadow,
        ],
        div![
            class![C.flex, C.justify_between, C.px_6, C._mb_px, C.bg_gray_200],
            h3![class![C.py_4, C.font_normal, C.text_lg], caption]
        ],
        T::wrapper_view(vec![
            T::thead_view(vec![
                T::th_left(plain!("Name")),
                T::th_left(plain!("Volume")),
                T::th_left(plain!("Primary Server")).merge_attrs(class![C.whitespace_no_wrap]),
                T::th_left(plain!("Failover Server")).merge_attrs(class![C.whitespace_no_wrap]),
                T::th_left(plain!("Started on")).merge_attrs(class![C.whitespace_no_wrap]),
            ]),
            tbody![tgts.iter().map(|t| tr![
                T::td_view(vec![
                    a![
                        class![C.text_blue_500, C.hover__underline],
                        attrs! {At::Href => Route::Target(RouteId::from(t.id)).to_href()},
                        &t.name
                    ],
                    span![class![C.mx_1], lock_indicator::view(&model.locks, &***t)],
                    alert_indicator(&model.records.active_alert, &***t, true, Placement::Top),
                ])
                .merge_attrs(class![C.whitespace_no_wrap]),
                T::td_view(volume_link(&model.records, t)).merge_attrs(class![C.w_4]),
                T::td_view(server_link(Some(&t.primary_server), &t.primary_server_name)),
                T::td_view(server_link(t.failover_servers.first(), &t.failover_server_name)),
                T::td_view(server_link(t.active_host.as_ref(), &t.active_host_name)),
                td!["TBD"],
            ])]
        ])
    ]
}

pub(crate) fn status_view<I, E: ResourceUri + ToCompositeId>(model: &Model, x: &E) -> Node<I> {
    span![
        class![C.whitespace_no_wrap],
        span![class![C.mx_1], lock_indicator::view(&model.locks, x)],
        alert_indicator(&model.records.active_alert, x, false, Placement::Top)
    ]
}

pub(crate) fn mgs<I>(tgts: &HashMap<u32, Arc<Target<TargetConfParam>>>, f: &Filesystem) -> Node<I> {
    if let Some(t) = tgts
        .values()
        .find(|t| t.kind == TargetKind::Mgt && f.mgt == t.resource_uri)
    {
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

fn is_fs_target(fs: &Filesystem, t: &Target<TargetConfParam>) -> bool {
    t.filesystem_id == Some(fs.id)
        || t.filesystems
            .as_ref()
            .and_then(|f| f.iter().find(|x| x.id == fs.id))
            .is_some()
}

fn server_link<I>(uri: Option<&String>, txt: &String) -> Node<I> {
    if let Some(u) = uri {
        let srv_id = extract_id(&u).unwrap();
        a![
            class![C.text_blue_500, C.hover__underline, C.block],
            attrs! {At::Href => Route::Server(RouteId::from(srv_id)).to_href()},
            txt
        ]
    } else {
        plain!("N/A")
    }
}

fn volume_link<I>(cache: &ArcCache, t: &Target<TargetConfParam>) -> Node<I> {
    let vol_id = match &t.volume {
        VolumeOrResourceUri::ResourceUri(url) => extract_id(&url).unwrap().parse::<u32>().unwrap(),
        VolumeOrResourceUri::Volume(v) => v.id,
    };

    if let Some(vn) = cache.volume_node.arc_values().find(|v| v.volume_id == vol_id) {
        let size = cache
            .volume
            .arc_values()
            .find(|v| v.id == vol_id)
            .map(|v| format!("({})", number_formatter::format_bytes(v.size.unwrap() as f64, None)))
            .unwrap();
        a![
            class![C.whitespace_no_wrap, C.text_blue_500, C.hover__underline, C.block],
            attrs! {At::Href => Route::Volume(RouteId::from(vol_id)).to_href()},
            vn.path,
            " ",
            size
        ]
    } else {
        plain!("N/A")
    }
}
