// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    components::{action_dropdown, alert_indicator, date, font_awesome, lnet_status, lock_indicator, panel, Placement},
    extensions::MergeAttrs as _,
    generated::css_classes::C,
    GMsg,
};

use emf_wire_types::{
    db::{CorosyncConfigurationRecord, LnetConfigurationRecord, PacemakerConfigurationRecord},
    warp_drive::{ArcCache, Locks},
    Host, Session, ToCompositeId,
};
use seed::{prelude::*, *};
use std::sync::Arc;

#[derive(Clone, Debug)]
pub enum Msg {
    ServerActionDropdown(action_dropdown::IdMsg),
    LnetActionDropdown(action_dropdown::IdMsg),
    PacemakerActionDropdown(action_dropdown::IdMsg),
    CorosyncActionDropdown(action_dropdown::IdMsg),
}

pub fn update(msg: Msg, cache: &ArcCache, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::ServerActionDropdown(x) => {
            let action_dropdown::IdMsg(y, msg) = x;

            action_dropdown::update(
                action_dropdown::IdMsg(y, msg),
                cache,
                &mut model.server_dropdown,
                &mut orders.proxy(Msg::ServerActionDropdown),
            );
        }
        Msg::LnetActionDropdown(msg) => {
            if let Some((_, d)) = model.lnet_config.as_mut() {
                action_dropdown::update(msg, cache, d, &mut orders.proxy(Msg::LnetActionDropdown));
            }
        }
        Msg::PacemakerActionDropdown(msg) => {
            if let Some((_, d)) = model.pacemaker_config.as_mut() {
                action_dropdown::update(msg, cache, d, &mut orders.proxy(Msg::PacemakerActionDropdown));
            }
        }
        Msg::CorosyncActionDropdown(msg) => {
            if let Some((_, d)) = model.corosync_config.as_mut() {
                action_dropdown::update(msg, cache, d, &mut orders.proxy(Msg::CorosyncActionDropdown));
            }
        }
    }
}

pub struct Model {
    pub server: Arc<Host>,
    lnet_config: Option<(Arc<LnetConfigurationRecord>, action_dropdown::Model)>,
    pacemaker_config: Option<(Arc<PacemakerConfigurationRecord>, action_dropdown::Model)>,
    corosync_config: Option<(Arc<CorosyncConfigurationRecord>, action_dropdown::Model)>,
    server_dropdown: action_dropdown::Model,
}

impl Model {
    pub fn new(
        server: Arc<Host>,
        lnet_config: Option<Arc<LnetConfigurationRecord>>,
        pacemaker_config: Option<Arc<PacemakerConfigurationRecord>>,
        corosync_config: Option<Arc<CorosyncConfigurationRecord>>,
    ) -> Self {
        Self {
            server_dropdown: action_dropdown::Model::new(vec![server.composite_id()]),
            lnet_config: lnet_config.map(|x| {
                let id = x.composite_id();

                (x, action_dropdown::Model::new(vec![id]))
            }),
            pacemaker_config: pacemaker_config.map(|x| {
                let id = x.composite_id();

                (x, action_dropdown::Model::new(vec![id]))
            }),
            corosync_config: corosync_config.map(|x| {
                let id = x.composite_id();

                (x, action_dropdown::Model::new(vec![id]))
            }),
            server,
        }
    }
}

pub fn view(
    cache: &ArcCache,
    model: &Model,
    all_locks: &Locks,
    session: Option<&Session>,
    sd: &date::Model,
) -> impl View<Msg> {
    nodes![
        panel::view(
            h3![
                class![C.py_4, C.font_normal, C.text_lg],
                &format!("Server: {}", model.server.fqdn),
                lock_indicator::view(all_locks, &model.server).merge_attrs(class![C.ml_2]),
                alert_indicator(&cache.active_alert, &model.server, true, Placement::Right).merge_attrs(class![C.ml_2]),
            ],
            div![
                class![C.grid, C.grid_cols_2, C.gap_4],
                div![class![C.px_6, C.py_4], "FQDN"],
                div![class![C.px_6, C.py_4], model.server.fqdn],
                div![class![C.px_6, C.py_4], "Boot time"],
                div![
                    class![C.px_6, C.py_4],
                    date_view(sd, &model.server.boot_time)
                ],
                action_dropdown::view(model.server.id, &model.server_dropdown, all_locks, session)
                    .merge_attrs(class![C.px_6, C.py_4, C.grid, C.col_span_2])
                    .map_msg(Msg::ServerActionDropdown)
            ],
        ),
        if let Some((x, lnet_dropdown)) = model.lnet_config.as_ref() {
            panel::view(
                h3![
                    class![C.py_4, C.font_normal, C.text_lg],
                    "LNet",
                    alert_indicator(&cache.active_alert, &x, true, Placement::Right)
                ],
                div![
                    class![C.grid, C.grid_cols_2, C.gap_4],
                    div![class![C.px_6, C.py_4], "State"],
                    div![class![C.px_6, C.py_4], lnet_status::view(x, all_locks)],
                    action_dropdown::view(model.server.id, lnet_dropdown, all_locks, session)
                        .merge_attrs(class![C.px_6, C.py_4, C.grid, C.col_span_2])
                        .map_msg(Msg::LnetActionDropdown),
                ],
            ).merge_attrs(class![C.mt_4])
        } else {
            empty![]
        }
        if let Some((x, pacemaker_dropdown)) = model.pacemaker_config.as_ref() {
            pacemaker_section(cache, x, pacemaker_dropdown, all_locks, session)
        } else {
              empty![]
        },
        if let Some((x, corosync_dropdown)) = model.corosync_config.as_ref() {
            corosync_section(cache, x, corosync_dropdown, all_locks, session)
        } else {
            empty![]
        }
    ]
}

fn pacemaker_section(
    cache: &ArcCache,
    x: &PacemakerConfigurationRecord,
    dropdown: &action_dropdown::Model,
    all_locks: &Locks,
    session: Option<&Session>,
) -> Node<Msg> {
    panel::view(
        h3![
            class![C.py_4, C.font_normal, C.text_lg],
            "Pacemaker",
            alert_indicator(&cache.active_alert, &x, true, Placement::Right)
        ],
        div![
            class![C.grid, C.grid_cols_2, C.gap_4],
            div![class![C.px_6, C.py_4], "State"],
            div![class![C.px_6, C.py_4], state(&x.state),],
            action_dropdown::view(x.id, dropdown, all_locks, session)
                .merge_attrs(class![C.px_6, C.py_4, C.grid, C.col_span_2])
                .map_msg(Msg::PacemakerActionDropdown),
        ],
    )
    .merge_attrs(class![C.mt_4])
}

fn corosync_section(
    cache: &ArcCache,
    x: &CorosyncConfigurationRecord,
    dropdown: &action_dropdown::Model,
    all_locks: &Locks,
    session: Option<&Session>,
) -> Node<Msg> {
    panel::view(
        h3![
            class![C.py_4, C.font_normal, C.text_lg],
            "Corosync",
            alert_indicator(&cache.active_alert, &x, true, Placement::Right)
        ],
        div![
            class![C.grid, C.grid_cols_2, C.gap_4],
            div![class![C.px_6, C.py_4], "State"],
            div![class![C.px_6, C.py_4], state(&x.state)],
            div![class![C.px_6, C.py_4], "Mcast Port"],
            div![
                class![C.px_6, C.py_4],
                x.mcast_port.map(|x| x.to_string()).unwrap_or_else(|| "---".into())
            ],
            action_dropdown::view(x.id, dropdown, all_locks, session)
                .merge_attrs(class![C.px_6, C.py_4, C.grid, C.col_span_2])
                .map_msg(Msg::CorosyncActionDropdown),
        ],
    )
    .merge_attrs(class![C.mt_4])
}

fn state<T>(state: &str) -> Node<T> {
    match state {
        "started" => span![
            font_awesome(class![C.w_4, C.h_4, C.inline, C.mr_1, C.text_green_500], "power-off"),
            "Started"
        ],
        "stopped" => span![
            font_awesome(class![C.w_4, C.h_4, C.inline, C.mr_1, C.text_gray_500], "power-off"),
            "Stopped"
        ],
        "unconfigured" => span!["Unconfigured"],
        _ => span!["---"],
    }
}

pub(crate) fn date_view<T>(sd: &date::Model, date: &Option<String>) -> Node<T> {
    if let Some(s) = date {
        match chrono::DateTime::parse_from_rfc3339(&format!("{}-00:00", s)) {
            Ok(d) => date::view(sd, &d),
            Err(e) => {
                error!(format!("could not parse the date: '{}': {}", s, e));
                plain![s.to_string()]
            }
        }
    } else {
        plain!["---"]
    }
}
