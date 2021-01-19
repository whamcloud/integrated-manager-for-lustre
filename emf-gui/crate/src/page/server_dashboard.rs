// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    components::{
        dashboard::dashboard_container,
        grafana_chart::{self, create_chart_params, EMF_METRICS_DASHBOARD_ID, EMF_METRICS_DASHBOARD_NAME},
    },
    generated::css_classes::C,
};
use emf_wire_types::warp_drive::ArcCache;
use seed::{class, div, prelude::*};

#[derive(Default)]
pub struct Model {
    pub host_name: String,
}

#[derive(Clone, Debug)]
pub enum Msg {}

pub fn view(_: &ArcCache, model: &Model) -> impl View<Msg> {
    div![
        class![C.grid, C.lg__grid_cols_2, C.gap_6],
        vec![
            dashboard_container::view(
                "Read/Write Bandwidth",
                div![
                    class![C.h_full, C.min_h_80, C.p_2],
                    grafana_chart::view(
                        EMF_METRICS_DASHBOARD_ID,
                        EMF_METRICS_DASHBOARD_NAME,
                        create_chart_params(6, "10s", vec![("host_name", &model.host_name)]),
                        "90%",
                    ),
                ],
            ),
            dashboard_container::view(
                "CPU Usage",
                div![
                    class![C.h_full, C.min_h_80, C.p_2],
                    grafana_chart::view(
                        EMF_METRICS_DASHBOARD_ID,
                        EMF_METRICS_DASHBOARD_NAME,
                        create_chart_params(10, "10s", vec![("host_name", &model.host_name)]),
                        "90%",
                    ),
                ],
            ),
            dashboard_container::view(
                "Memory Usage",
                div![
                    class![C.h_full, C.min_h_80, C.p_2],
                    grafana_chart::view(
                        EMF_METRICS_DASHBOARD_ID,
                        EMF_METRICS_DASHBOARD_NAME,
                        create_chart_params(8, "10s", vec![("host_name", &model.host_name)]),
                        "90%",
                    ),
                ],
            ),
            dashboard_container::view(
                "LNET Usage",
                div![
                    class![C.h_full, C.min_h_80, C.p_2],
                    grafana_chart::view(
                        EMF_METRICS_DASHBOARD_ID,
                        EMF_METRICS_DASHBOARD_NAME,
                        create_chart_params(36, "10s", vec![("host_name", &model.host_name)]),
                        "90%",
                    ),
                ],
            ),
        ]
    ]
}
