// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    components::{chart::fs_usage, dashboard::dashboard_container, progress_circle},
    extensions::MergeAttrs,
    generated::css_classes::C,
};
use seed::{prelude::*, *};

pub fn view<T>(model: &fs_usage::Model) -> Node<T> {
    if let Some(metrics) = &model.metric_data {
        let color = progress_circle::used_to_color(model.percent_used);

        let dashboard_chart = div![
            class![C.grid, C.grid_cols_3, C.gap_2, C.items_center, C.h_full, C.min_h_80],
            div![
                class![C.justify_self_end, C.p_2],
                p![class![color], number_formatter::format_bytes(metrics.bytes_used, 1)],
                p![class![C.text_gray_500, C.text_xs], "(Used)"]
            ],
            progress_circle::view((model.percent_used, color)).merge_attrs(class![
                C.justify_self_center,
                C.w_full,
                C.h_full
            ]),
            div![
                class![C.p_2],
                p![
                    class![C.text_gray_600],
                    number_formatter::format_bytes(metrics.bytes_avail, 1)
                ],
                p![class![C.text_gray_500, C.text_xs], "(Available)"]
            ]
        ];

        dashboard_container::view("Filesystem Space Usage", dashboard_chart)
    } else {
        dashboard_container::view("Filesystem Space Usage", progress_circle::view(None))
    }
}
