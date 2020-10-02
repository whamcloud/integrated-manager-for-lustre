// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::generated::css_classes::C;
use seed::{prelude::*, *};

static RADIUS: f64 = 90.0;
static CIRCUMFERENCE: f64 = 2.0 * std::f64::consts::PI * RADIUS;

pub fn used_to_color(used: f64) -> &'static str {
    if used.is_nan() {
        C.text_gray_500
    } else {
        match used.round() as u64 {
            75..=100 => C.text_red_500,
            50..=74 => C.text_yellow_500,
            0..=49 => C.text_green_500,
            _ => C.text_gray_500,
        }
    }
}

pub fn view<'a, T>(x: impl Into<Option<(f64, &'a str)>>) -> Node<T> {
    match x.into() {
        Some((used, color)) => {
            let stroke_length = (100.0f64 - used) / 100.0f64 * CIRCUMFERENCE;

            svg![
                class![C.stroke_current, C.fill_current],
                attrs! {
                  At::ViewBox => "0 0 190 190"
                },
                g![
                    class![C._rotate_90, C.transform, C.origin_center],
                    circle![
                        class![
                            C.stroke_5,
                            C.text_gray_200,
                            C.transition_stroke_dashoffset,
                            C.duration_500,
                            C.ease_linear
                        ],
                        attrs! {
                          At::R => "90",
                          At::Cx => "95",
                          At::Cy => "95",
                          At::Fill => "transparent",
                        }
                    ],
                    circle![
                        class![
                            C.stroke_5,
                            color,
                            C.transition_stroke_dashoffset,
                            C.duration_500,
                            C.ease_linear
                        ],
                        attrs! {
                          At::R => "90",
                          At::Cx => "95",
                          At::Cy => "95",
                          At::Fill => "transparent",
                          At::StrokeDashArray => CIRCUMFERENCE,
                          At::StrokeDashOffset => stroke_length
                        }
                    ],
                    text![
                        class![
                            C.rotate_90
                            C.origin_center,
                            C.stroke_2,
                            C.text_4xl,
                            C.transform,
                            color,
                        ],
                        attrs! {
                          At::X => "50%",
                          At::Y => "50%",
                          At::DominantBaseline => "central",
                          At::TextAnchor => "middle"
                        },
                        tspan![format!("{}", used as u16)],
                        tspan![class![C.text_gray_400], "%"]
                    ]
                ],
            ]
        }
        None => div!["Loading"],
    }
}
