// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    components::{dropdown, font_awesome, Placement},
    extensions::NodeExt as _,
    generated::css_classes::C,
    GMsg,
};
use seed::{prelude::*, virtual_dom::Attrs, *};
use std::{cmp::Eq, fmt::Debug, ops::Range};

pub const ROW_OPTS: [usize; 4] = [10, 25, 50, 100];

#[derive(Debug, Eq, PartialEq)]
pub struct Model {
    pub total: usize,
    limit: usize,
    offset: usize,
    dropdown: dropdown::Model,
}

impl Default for Model {
    fn default() -> Self {
        Self {
            limit: ROW_OPTS[0],
            total: 0,
            offset: 0,
            dropdown: dropdown::Model::default(),
        }
    }
}

impl Model {
    pub fn new(total: usize) -> Self {
        Self {
            total,
            ..Default::default()
        }
    }
    pub const fn has_more(&self) -> bool {
        self.limit + self.offset < self.total()
    }
    pub const fn total(&self) -> usize {
        self.total
    }
    pub const fn limit(&self) -> usize {
        self.limit
    }
    pub const fn has_less(&self) -> bool {
        self.offset != 0
    }
    pub fn has_pages(&self) -> bool {
        self.has_more() || self.has_less()
    }
    pub const fn offset(&self) -> usize {
        self.offset
    }
    pub fn end(&self) -> usize {
        std::cmp::min(self.offset + self.limit, self.total())
    }
    pub fn prev_page(&mut self) {
        self.offset = if self.limit > self.offset {
            0
        } else {
            self.offset - self.limit
        };
    }
    pub fn next_page(&mut self) {
        self.offset = self.end();
    }
    pub fn range(&self) -> Range<usize> {
        self.offset..self.end()
    }
}

#[derive(Clone, Debug)]
pub enum Msg {
    Dropdown(dropdown::Msg),
    Next,
    Noop,
    Prev,
    SetLimit(usize),
    SetOffset(usize),
    SetTotal(usize),
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::SetTotal(total) => {
            model.total = total;
        }
        Msg::SetOffset(offset) => {
            model.offset = offset;
        }
        Msg::SetLimit(limit) => {
            model.limit = limit;
            orders.send_msg(Msg::Dropdown(dropdown::Msg::Close));
        }
        Msg::Next => {
            model.next_page();
        }
        Msg::Prev => {
            model.prev_page();
        }
        Msg::Dropdown(msg) => {
            dropdown::update(msg, &mut model.dropdown);
        }
        Msg::Noop => {}
    }
}

#[derive(Debug, Clone, Copy, Eq, PartialEq)]
pub enum Dir {
    Asc,
    Desc,
}

impl Default for Dir {
    fn default() -> Self {
        Self::Asc
    }
}

impl Dir {
    pub fn next(self) -> Self {
        match self {
            Self::Asc => Self::Desc,
            Self::Desc => Self::Asc,
        }
    }
}

// View

/// Given a direction, renders the correct chevron for that direction.
pub fn dir_toggle_view<T>(dir: Dir, more_attrs: Attrs) -> Node<T> {
    let x = match dir {
        Dir::Asc => "chevron-up",
        Dir::Desc => "chevron-down",
    };

    font_awesome(more_attrs, x)
}

pub(crate) fn limit_selection_view(model: &Model) -> Node<Msg> {
    if !model.has_pages() {
        return empty![];
    }

    let btn = button![
        class![
            C.bg_blue_700 => model.dropdown.is_open(),
            C.bg_transparent => model.dropdown.is_closed(),
            C.border_blue_500 => model.dropdown.is_closed(),
            C.border_transparent => model.dropdown.is_open(),
            C.border,
            C.focus__outline_none,
            C.hover__bg_blue_700,
            C.hover__border_transparent,
            C.hover__text_white
            C.px_3,
            C.py_1,
            C.rounded_full,
            C.text_blue_500 => model.dropdown.is_closed(),
            C.text_sm,
            C.text_white => model.dropdown.is_open(),
        ],
        model.limit.to_string(),
        simple_ev(Ev::Blur, Msg::Dropdown(dropdown::Msg::Close)),
        simple_ev(Ev::Click, Msg::Dropdown(dropdown::Msg::Toggle)),
        font_awesome(class![C.w_3, C.h_3, C.inline, C._mt_1], "chevron-up")
    ];

    div![
        class![C.mr_3],
        span![class![C.mr_1, C.text_sm], "Rows per page:"],
        span![
            class![C.relative],
            btn,
            dropdown::wrapper_view(
                Placement::Top,
                model.dropdown.is_open(),
                ROW_OPTS
                    .iter()
                    .map(|x| {
                        dropdown::item_view(a![x.to_string()])
                            .with_listener(ev(Ev::MouseDown, move |ev| {
                                ev.prevent_default();
                                Msg::Noop
                            }))
                            .with_listener(simple_ev(Ev::Click, Msg::SetLimit(*x)))
                    })
                    .collect::<Vec<_>>()
            )
        ],
    ]
}

/// Given a paging `Model`, renders the current range and total records.
pub fn page_count_view<T>(p: &Model) -> Node<T> {
    span![
        class![C.self_center, C.text_sm, C.mr_1],
        &format!("{} - {} of {}", p.offset() + 1, p.end(), p.total())
    ]
}

/// Given a paging `Model`, renders left and right chevrons if there are pages.
pub fn next_prev_view(paging: &Model) -> Vec<Node<Msg>> {
    if !paging.has_pages() {
        return vec![];
    }

    let cls = class![
        C.hover__underline,
        C.select_none,
        C.hover__text_gray_300,
        C.cursor_pointer
    ];

    vec![
        a![
            &cls,
            class![
                C.px_5,
                C.pointer_events_none => !paging.has_less(),
                C.text_gray_700 => !paging.has_less(),
            ],
            font_awesome(class![C.w_5, C.h_4, C.inline, C.mr_1, C._mt_1], "chevron-left"),
            simple_ev(Ev::Click, Msg::Prev),
            "prev"
        ],
        a![
            &cls,
            class![
                C.pointer_events_none => !paging.has_more(),
                C.text_gray_700 => !paging.has_more(),
            ],
            "next",
            simple_ev(Ev::Click, Msg::Next),
            font_awesome(class![C.w_5, C.h_4, C.inline, C.mr_1, C._mt_1], "chevron-right")
        ],
    ]
}

#[cfg(test)]
mod tests {
    use super::Model;

    #[test]
    fn test_paging_less() {
        let mut pager = Model::new(20);

        assert!(!pager.has_less());

        pager.next_page();

        assert!(pager.has_less());
    }

    #[test]
    fn test_paging_more() {
        let mut pager = Model::new(20);

        assert!(pager.has_more());

        pager.next_page();

        assert!(!pager.has_more());
    }

    #[test]
    fn test_paging_end() {
        let mut pager = Model::new(20);

        assert_eq!(pager.end(), 10);

        pager.next_page();

        assert_eq!(pager.end(), 20);
    }

    #[test]
    fn test_has_pages() {
        let mut pager = Model::default();

        assert!(!pager.has_pages());

        pager.total = 10;

        assert!(!pager.has_pages());

        pager.total = 11;

        assert!(pager.has_pages());
    }

    #[test]
    fn test_single_record() {
        let pager = Model::new(1);

        assert_eq!(pager.range(), 0..1);
    }

    #[test]
    fn test_range() {
        let mut pager = Model::new(20);

        assert_eq!(pager.range(), 0..10);

        pager.limit = 20;

        assert_eq!(pager.range(), 0..20);

        pager.next_page();

        assert!(!pager.has_more());

        assert_eq!(pager.range(), 20..20);
    }
}
