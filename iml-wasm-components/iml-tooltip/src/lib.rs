// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use seed::{class, div, prelude::*, span, style};

#[derive(Default, Debug)]
pub struct Model {
    pub placement: TooltipPlacement,
    pub size: TooltipSize,
    pub error_tooltip: bool,
    pub open: bool,
}

#[derive(serde::Deserialize, serde::Serialize, Debug, PartialEq, Clone, Copy)]
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
    Model {
        placement,
        size,
        error_tooltip,
        open,
    }: &Model,
) -> Node<T> {
    let class = if *error_tooltip { "error-tooltip" } else { "" };

    let style = if *open {
        style! { "display" => "block"; "opacity" => "0.9" }
    } else {
        style! {}
    };

    div![
        style,
        class!["tooltip inferno-tt", placement.into(), size.into(), class],
        div![class!["tooltip-arrow"]],
        div![class!["tooltip-inner"], span![El::from_html(&message)]]
    ]
}
