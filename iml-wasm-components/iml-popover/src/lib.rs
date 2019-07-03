// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use seed::{class, div, h3, prelude::*};

#[derive(Debug, Clone)]
pub enum Placement {
    Left,
    Right,
    Top,
    Bottom,
}

impl From<&Placement> for &str {
    fn from(p: &Placement) -> Self {
        match p {
            Placement::Left => "left",
            Placement::Right => "right",
            Placement::Top => "top",
            Placement::Bottom => "bottom",
        }
    }
}

impl Default for Placement {
    fn default() -> Self {
        Placement::Left
    }
}

pub fn popover<T>(open: bool, placement: &Placement, children: Vec<El<T>>) -> El<T> {
    if !open {
        return seed::empty();
    }

    div![
        class!["fade", "popover", "in", placement.into()],
        div![class!["arrow"]],
        children
    ]
}

pub fn popover_title<T>(el: El<T>) -> El<T> {
    h3![class!["popover-title"], el]
}

pub fn popover_content<T>(el: El<T>) -> El<T> {
    div![class!["popover-content"], el]
}
