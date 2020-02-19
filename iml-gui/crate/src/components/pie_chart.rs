// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use seed::{attrs, circle, path, prelude::*, style, svg};
use std::f64::consts::PI;

pub(crate) fn pie_chart<T>(ratio: f64) -> Node<T> {
    let radians = 2.0 * PI * ratio;
    let end_x = radians.cos();
    let end_y = radians.sin();
    let large_arc_flag = if ratio > 0.5 { 1 } else { 0 }; // FIXME: negative ratio?

    let d = format!("M 1 0 A 1 1 0 {} 1 {} {} L 0 0", large_arc_flag, end_x, end_y);

    svg![
        attrs! { At::ViewBox => "-1 -1 2 2" },
        style! {
            "transform" =>  "rotate(-0.25turn)"
        },
        circle![attrs! { At::R => "1", At::Fill => "#aec7e8"}],
        path![attrs! { At::D => d, At::Fill => "#1f77b4"}]
    ]
}
