// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    components::{
        datepicker,
        grafana_chart::{self, create_chart_params, EMF_METRICS_DASHBOARD_ID, EMF_METRICS_DASHBOARD_NAME},
    },
    generated::css_classes::C,
};
use seed::{prelude::*, *};

pub(crate) mod dashboard_container;
pub(crate) mod dashboard_fs_usage;

pub(crate) fn performance_container(
    model: &datepicker::Model,
    bw_id: u16,
    iops_id: u16,
    vars: impl IntoIterator<Item = (impl ToString, impl ToString)> + Clone,
) -> Node<datepicker::Msg> {
    div![
        class![C.h_full, C.min_h_80, C.px_2],
        div![
            class![C.text_center],
            p![
                class![
                    C.inline_block,
                    C.bg_throughput_background,
                    C.rounded_full,
                    C.px_2,
                    C.text_xs,
                    C.text_white
                ],
                "Throughput"
            ],
        ],
        grafana_chart::view(
            EMF_METRICS_DASHBOARD_ID,
            EMF_METRICS_DASHBOARD_NAME,
            create_chart_params(bw_id, "10s", vars.clone()),
            "38%",
        ),
        div![
            class![C.text_center],
            p![
                class![
                    C.inline_block,
                    C.bg_green_400,
                    C.rounded_full,
                    C.px_2,
                    C.text_xs,
                    C.text_white
                ],
                "IOPS"
            ],
        ],
        grafana_chart::view(
            EMF_METRICS_DASHBOARD_ID,
            EMF_METRICS_DASHBOARD_NAME,
            create_chart_params(iops_id, "10s", vars),
            "38%",
        ),
        datepicker::view(model),
    ]
}
