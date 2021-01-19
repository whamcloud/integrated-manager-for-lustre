// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    components::{
        dashboard::{dashboard_container, performance_container},
        datepicker,
        grafana_chart::{self, create_chart_params, EMF_METRICS_DASHBOARD_ID, EMF_METRICS_DASHBOARD_NAME},
    },
    generated::css_classes::C,
    GMsg,
};
use emf_wire_types::warp_drive::ArcCache;
use seed::{prelude::*, *};

#[derive(Default)]
pub struct Model {
    pub target_name: String,
    pub io_date_picker: datepicker::Model,
}

#[derive(Clone, Debug)]
pub enum Msg {
    IoChart(datepicker::Msg),
}

pub enum TargetDashboard {
    MdtDashboard,
    OstDashboard,
}

impl From<&str> for TargetDashboard {
    fn from(item: &str) -> Self {
        if item.contains("OST") {
            Self::OstDashboard
        } else {
            Self::MdtDashboard
        }
    }
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::IoChart(msg) => {
            datepicker::update(msg, &mut model.io_date_picker, &mut orders.proxy(Msg::IoChart));
        }
    }
}

pub fn view(_: &ArcCache, model: &Model) -> Node<Msg> {
    let dashboard_type: TargetDashboard = (model.target_name.as_str()).into();

    div![
        class![C.grid, C.lg__grid_cols_2, C.gap_6],
        match dashboard_type {
            TargetDashboard::MdtDashboard => vec![
                dashboard_container::view(
                    "Metadata Operations",
                    div![
                        class![C.h_full, C.min_h_80, C.p_2],
                        grafana_chart::view(
                            EMF_METRICS_DASHBOARD_ID,
                            EMF_METRICS_DASHBOARD_NAME,
                            create_chart_params(37, "10s", vec![("target_name", &model.target_name)]),
                            "90%",
                        ),
                    ],
                ),
                dashboard_container::view(
                    "Space Usage",
                    div![
                        class![C.h_full, C.min_h_80, C.p_2],
                        grafana_chart::view(
                            EMF_METRICS_DASHBOARD_ID,
                            EMF_METRICS_DASHBOARD_NAME,
                            create_chart_params(14, "10s", vec![("target_name", &model.target_name)]),
                            "90%",
                        ),
                    ],
                ),
                dashboard_container::view(
                    "File Usage",
                    div![
                        class![C.h_full, C.min_h_80, C.p_2],
                        grafana_chart::view(
                            EMF_METRICS_DASHBOARD_ID,
                            EMF_METRICS_DASHBOARD_NAME,
                            create_chart_params(16, "10s", vec![("target_name", &model.target_name)]),
                            "90%",
                        ),
                    ],
                )
            ],
            TargetDashboard::OstDashboard => vec![
                dashboard_container::view(
                    "I/O Performance",
                    performance_container(
                        &model.io_date_picker,
                        39,
                        38,
                        vec![
                            ("target_name", &model.target_name),
                            ("from", &model.io_date_picker.from),
                            ("to", &model.io_date_picker.to)
                        ]
                    )
                    .map_msg(Msg::IoChart),
                ),
                dashboard_container::view(
                    "Space Usage",
                    div![
                        class![C.h_full, C.min_h_80, C.p_2],
                        grafana_chart::view(
                            EMF_METRICS_DASHBOARD_ID,
                            EMF_METRICS_DASHBOARD_NAME,
                            create_chart_params(14, "10s", vec![("target_name", &model.target_name)]),
                            "90%",
                        ),
                    ],
                ),
                dashboard_container::view(
                    "Object Usage",
                    div![
                        class![C.h_full, C.min_h_80, C.p_2],
                        grafana_chart::view(
                            EMF_METRICS_DASHBOARD_ID,
                            EMF_METRICS_DASHBOARD_NAME,
                            create_chart_params(16, "10s", vec![("target_name", &model.target_name)]),
                            "90%",
                        ),
                    ],
                )
            ],
        }
    ]
}
