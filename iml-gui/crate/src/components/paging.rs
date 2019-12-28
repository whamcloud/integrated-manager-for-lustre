use crate::generated::css_classes::C;
use crate::{components::font_awesome, WatchState};
use iml_wire_types::warp_drive::Cache;
use indexmap::IndexSet;
use seed::{prelude::*, virtual_dom::Attrs, *};
use std::{cmp::Eq, fmt::Debug, hash::Hash, iter::FromIterator};

#[derive(Debug, Eq, PartialEq)]
pub struct Model<T: Debug + Eq + Hash> {
    pub items: IndexSet<T>,
    pub limit: usize,
    offset: usize,
    pub dir: Dir,
    pub dropdown: WatchState,
}

pub const ROW_OPTS: [usize; 4] = [10, 25, 50, 100];

#[derive(Debug, Clone, Copy, Eq, PartialEq)]
pub enum Dir {
    Asc,
    Desc,
}

impl<T: Debug + Eq + Hash> Default for Model<T> {
    fn default() -> Self {
        Model {
            items: IndexSet::new(),
            limit: ROW_OPTS[0],
            offset: 0,
            dir: Dir::Asc,
            dropdown: Default::default(),
        }
    }
}

impl<T: Debug + Eq + Hash> Model<T> {
    pub fn new(items: impl IntoIterator<Item = T>) -> Self {
        Model {
            items: IndexSet::from_iter(items),
            ..Model::default()
        }
    }
    pub fn has_more(&self) -> bool {
        self.limit + self.offset < self.total()
    }
    pub fn total(&self) -> usize {
        self.items.len()
    }
    pub fn has_less(&self) -> bool {
        self.offset != 0
    }

    pub fn has_pages(&self) -> bool {
        self.has_more() || self.has_less()
    }

    pub fn offset(&self) -> usize {
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
        self.offset = std::cmp::min(self.offset + self.limit, self.total() - 1);
    }
    pub fn slice_page(&self) -> impl Iterator<Item = &T> {
        self.items.iter().skip(self.offset()).take(self.end())
    }
}

#[derive(Clone)]
pub enum Msg<T: Debug + Eq + Hash> {
    Next,
    Prev,
    Add(T),
    Remove(T),
    Dropdown(WatchState),
    Sort(Sort<T>),
    ToggleDir,
}

type Sort<T> = fn(&Cache, &Model<T>) -> IndexSet<T>;

pub fn update<T: Debug + Eq + Hash>(cache: &Cache, msg: Msg<T>, model: &mut Model<T>) {
    match msg {
        Msg::Next => {
            model.next_page();
        }
        Msg::Prev => {
            model.prev_page();
        }
        Msg::Dropdown(state) => {
            model.dropdown = state;
        }
        Msg::Add(t) => {
            model.items.insert(t);
        }
        Msg::Remove(t) => {
            model.items.shift_remove(&t);
        }
        Msg::Sort(sort) => {
            let xs = sort(cache, model);

            if model.dir == Dir::Desc {
                model.items = xs.into_iter().rev().collect()
            } else {
                model.items = xs;
            }
        }
        Msg::ToggleDir => {
            model.dir = if model.dir == Dir::Asc { Dir::Desc } else { Dir::Asc };
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

pub fn page_selection_view<T: Debug + Eq + Hash>(_open: bool, rows: usize) -> Node<Msg<T>> {
    let mut btn = button![
        class![
            C.bg_transparent,
            C.border,
            C.border_blue_500,
            C.text_blue_500,
            C.text_sm,
            C.py_1,
            C.px_3,
            C.rounded_full,
            C.hover__border_transparent,
            C.hover__bg_blue_700,
            C.hover__text_white
        ],
        rows.to_string(),
        font_awesome(class![C.w_3, C.h_3, C.inline], "chevron-up")
    ];

    btn.add_listener(mouse_ev(Ev::Click, |_| Msg::Dropdown(WatchState::Watching)));

    btn
}

pub fn paging_view<T: Debug + Eq + Hash + Clone>(p: &Model<T>) -> Node<Msg<T>> {
    let cls = class![
        C.hover__underline,
        C.select_none,
        C.text_gray_500,
        C.hover__text_gray_400,
        C.cursor_pointer
    ];

    div![
        class![C.flex, C.justify_end, C.py_1],
        div![
            class![C.mr_3],
            span![class![C.mr_1, C.text_sm], "Rows per page:"],
            page_selection_view(p.dropdown.is_open(), p.limit),
        ],
        span![
            class![C.self_center, C.text_sm, C.mr_1],
            &format!("{} - {} of {}", p.offset() + 1, p.end(), p.total())
        ],
        div![
            class![C.self_center],
            a![
                &cls,
                class![
                    C.pointer_events_none => !p.has_less(),
                    C.text_gray_300 => !p.has_less()
                ],
                simple_ev(Ev::Click, Msg::Prev),
                font_awesome(class![C.w_3, C.h_3, C.inline], "chevron-left")
            ],
            a![
                &cls,
                class![
                    C.mr_3,
                    C.pointer_events_none => !p.has_more(),
                    C.text_gray_300 => !p.has_more(),
                ],
                simple_ev(Ev::Click, Msg::Next),
                font_awesome(class![C.w_3, C.h_3, C.inline, C.ml_1,], "chevron-right")
            ]
        ]
    ]
}
