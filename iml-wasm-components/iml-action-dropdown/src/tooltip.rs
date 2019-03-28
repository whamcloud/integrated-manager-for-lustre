// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::Msg;
use seed::{class, div, prelude::*, span};

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

/// A tooltip component
pub fn tooltip_component(
    message: &str,
    placement: &TooltipPlacement,
    size: &TooltipSize,
    more_classes: Option<Vec<&str>>,
) -> El<Msg> {
    let more_classes = match more_classes {
        Some(classes) => classes.join(" "),
        None => "".to_string(),
    };

    div![
        class![
            "tooltip inferno-tt",
            placement.into(),
            size.into(),
            more_classes.as_str()
        ],
        div![class!["tooltip-arrow"]],
        div![class!["tooltip-inner"], span![El::from_html(&message)]]
    ]
}
