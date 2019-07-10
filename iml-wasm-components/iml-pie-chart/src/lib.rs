// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use seed::{attrs, circle, path, prelude::*, style, svg};
use std::f64::consts::PI;

/// Create a pie chart to display used / total as percentages
pub fn pie_chart<T>(used: f64, total: f64, total_color: &str, used_color: &str) -> El<T> {
    let (percent, radians) = if total == 0.0 {
        (0.0, 0.0)
    } else {
        let percent = used / total;
        (percent, 2.0 * PI * percent)
    };

    let end_x = radians.cos();
    let end_y = radians.sin();
    let large_arc_flag = if percent > 0.5 { 1 } else { 0 };

    let d = format!(
        "M 1 0 A 1 1 0 {} 1 {} {} L 0 0",
        large_arc_flag, end_x, end_y
    );

    svg![
        attrs! { At::ViewBox => "-1 -1 2 2" },
        style! {
            "transform" =>  "rotate(-0.25turn)"
        },
        circle![attrs! { "r" => "1"}, style! {"fill" => total_color}],
        path![attrs! { At::D => d}, style! {"fill" => used_color}]
    ]
}
