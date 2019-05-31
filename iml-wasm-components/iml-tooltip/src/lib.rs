// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use seed::{class, div, prelude::*, span};

#[derive(Default)]
pub struct Model {
    pub placement: TooltipPlacement,
    pub size: TooltipSize,
}

#[derive(serde::Deserialize, serde::Serialize, Debug, PartialEq, Clone)]
#[serde(rename_all = "lowercase")]
pub enum TooltipPlacement {
    Left,
    Right,
    Top,
    Bottom,
}

impl From<&TooltipPlacement> for &str {
    fn from(p: &TooltipPlacement) -> Self {
        match p {
            TooltipPlacement::Left => "left",
            TooltipPlacement::Right => "right",
            TooltipPlacement::Top => "top",
            TooltipPlacement::Bottom => "bottom",
        }
    }
}

impl Default for TooltipPlacement {
    fn default() -> Self {
        TooltipPlacement::Left
    }
}

#[derive(serde::Deserialize, serde::Serialize, Debug, PartialEq, Clone)]
#[serde(rename_all = "lowercase")]
pub enum TooltipSize {
    XSmall,
    Small,
    Medium,
    Large,
}

impl From<&TooltipSize> for &str {
    fn from(s: &TooltipSize) -> Self {
        match s {
            TooltipSize::XSmall => "xsmall",
            TooltipSize::Small => "small",
            TooltipSize::Medium => "medium",
            TooltipSize::Large => "large",
        }
    }
}

impl Default for TooltipSize {
    fn default() -> Self {
        TooltipSize::Large
    }
}

/// A tooltip
pub fn tooltip<T>(
    message: &str,
    Model { placement, size }: &Model
) -> El<T> {
    

    div![
        class![
            "tooltip inferno-tt",
            placement.into(),
            size.into()
        ],
        div![class!["tooltip-arrow"]],
        div![class!["tooltip-inner"], span![El::from_html(&message)]]
    ]
}
