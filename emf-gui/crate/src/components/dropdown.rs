// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{components::Placement, generated::css_classes::C};
use seed::{prelude::*, Style, *};
use std::mem;

#[derive(Debug, Clone, Copy, Eq, PartialEq)]
pub enum Model {
    Open,
    Close,
}

impl Model {
    pub fn is_open(self) -> bool {
        self == Self::Open
    }
    pub fn is_closed(self) -> bool {
        !self.is_open()
    }
}

impl Default for Model {
    fn default() -> Self {
        Self::Close
    }
}

#[derive(Clone, Debug)]
pub enum Msg {
    Close,
    Open,
    Toggle,
}

pub fn update(msg: Msg, model: &mut Model) {
    match msg {
        Msg::Open => {
            let _ = mem::replace(model, Model::Open);
        }
        Msg::Close => {
            let _ = mem::replace(model, Model::Close);
        }
        Msg::Toggle => {
            let next_state = match model {
                Model::Open => Model::Close,
                Model::Close => Model::Open,
            };

            let _ = mem::replace(model, next_state);
        }
    }
}

pub fn wrapper_view<T>(placement: Placement, open: bool, children: impl View<T>) -> Node<T> {
    if !open {
        return empty![];
    }

    let st = match placement {
        Placement::Top => {
            style! {
                St::Transform => "translate(50%, -100%)",
                St::Top => 0,
                St::Right => percent(50),
                St::MarginTop => px(-10),
            }
        }
        Placement::Bottom => {
            style! {
                St::Transform => "translateX(50%)",
                St::Top => percent(100),
                St::Right => percent(50),
                St::MarginTop => px(3),
                St::PaddingTop => px(5)
            }
        }
        _ => Style::empty(),
    };

    div![
        class![
            C.mt_2,
            C.py_2,
            C.cursor_pointer,
            C.text_center,
            C.bg_white,
            C.rounded_lg,
            C.shadow_xl,
            C.absolute
        ],
        st,
        children.els()
    ]
}

pub fn item_view<T>(children: impl View<T>) -> Node<T> {
    div![
        class![
            C.bg_gray_100,
            C.hover__bg_blue_700,
            C.hover__text_white,
            C.m_2,
            C.p_2,
            C.rounded,
            C.text_gray_800,
        ],
        children.els()
    ]
}
