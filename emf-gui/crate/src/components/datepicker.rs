// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{generated::css_classes::C, GMsg};
use seed::{class, div, prelude::*, *};

#[derive(Clone, PartialEq, Debug)]
pub enum ChartDuration {
    Day,
    TwoDays,
    Week,
}

#[derive(Clone, Debug)]
pub enum Msg {
    SelectDuration(ChartDuration),
}

pub struct Model {
    duration: ChartDuration,
    pub from: String,
    pub to: String,
}

impl<'a> Default for Model {
    fn default() -> Self {
        Self {
            duration: ChartDuration::Day,
            from: "now-1d".into(),
            to: "now".into(),
        }
    }
}

pub fn update(msg: Msg, model: &mut Model, _: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::SelectDuration(duration) => {
            match duration {
                ChartDuration::Day => {
                    model.from = "now-1d".into();
                    model.to = "now".into();
                }
                ChartDuration::TwoDays => {
                    model.from = "now-2d".into();
                    model.to = "now".into();
                }
                ChartDuration::Week => {
                    model.from = "now-1w".into();
                    model.to = "now".into();
                }
            }

            model.duration = duration;
        }
    }
}

pub fn view(model: &Model) -> Node<Msg> {
    div![
        class![C.text_center],
        div![
            class![C.inline_block, C.rounded_full, C.px_2, C.text_gray_400, C.text_xs,],
            button![
                class![
                    C.inline_block,
                    C.bg_blue_500 => model.duration == ChartDuration::Day,
                    C.bg_gray_200 => model.duration != ChartDuration::Day,
                    C.px_6,
                    C.rounded_l_full,
                    C.text_white => model.duration == ChartDuration::Day,
                ],
                "Day",
                simple_ev(Ev::Click, Msg::SelectDuration(ChartDuration::Day))
            ],
            button![
                class![
                    C.inline_block,
                    C.bg_blue_500 => model.duration == ChartDuration::TwoDays,
                    C.bg_gray_200 => model.duration != ChartDuration::TwoDays,
                    C.px_6,
                    C.border_l,
                    C.border_r,
                    C.border_white,
                    C.border_l_2,
                    C.border_r_2,
                    C.text_white => model.duration == ChartDuration::TwoDays,
                ],
                "2 Days",
                simple_ev(Ev::Click, Msg::SelectDuration(ChartDuration::TwoDays))
            ],
            button![
                class![
                    C.inline_block,
                    C.px_6,
                    C.bg_blue_500 => model.duration == ChartDuration::Week,
                    C.bg_gray_200 => model.duration != ChartDuration::Week,
                    C.rounded_r_full,
                    C.text_white => model.duration == ChartDuration::Week,
                ],
                "Week",
                simple_ev(Ev::Click, Msg::SelectDuration(ChartDuration::Week))
            ],
        ],
    ]
}
