// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{components::paging, extensions::MergeAttrs, generated::css_classes::C};
use seed::{prelude::*, Attrs, *};

pub fn wrapper_cls() -> Attrs {
    class![C.table_auto, C.w_full]
}

pub fn wrapper_view<T>(children: impl View<T>) -> Node<T> {
    table![
        wrapper_cls(),
        style! {
            St::BorderSpacing => px(10),
            St::BorderCollapse => "initial"
        },
        children.els()
    ]
}

pub fn thead_view<T>(children: impl View<T>) -> Node<T> {
    thead![style! { St::BorderSpacing => "0 10px"}, tr![children.els()]]
}

pub fn th_cls() -> Attrs {
    class![C.px_3, C.text_gray_800, C.font_normal]
}

pub fn th_view<T>(children: impl View<T>) -> Node<T> {
    th![th_cls(), children.els()]
}

pub fn th_left<T>(children: impl View<T>) -> Node<T> {
    th![th_cls(), class![C.text_left], children.els()]
}

pub fn th_right<T>(children: impl View<T>) -> Node<T> {
    th![th_cls(), class![C.text_right], children.els()]
}

pub fn th_sortable_cls() -> Attrs {
    class![C.border_b_2, C.border_blue_500]
}

pub fn td_cls() -> Attrs {
    class![C.px_3, C.bg_gray_100, C.rounded, C.p_4]
}

pub fn td_view<T>(children: impl View<T>) -> Node<T> {
    td![td_cls(), children.els()]
}

pub fn td_right<T>(children: impl View<T>) -> Node<T> {
    td_view(children).merge_attrs(class![C.text_right])
}

pub fn td_center<T>(children: impl View<T>) -> Node<T> {
    td_view(children).merge_attrs(class![C.text_center])
}

#[derive(Clone, Copy, Debug)]
pub struct SortBy<T>(pub T);

pub fn sort_header<T: PartialEq + Copy>(label: &str, sort_by: T, current_sort: T, dir: paging::Dir) -> Node<SortBy<T>> {
    let is_active = current_sort == sort_by;

    let table_cls = class![C.text_center];

    let table_cls = if is_active {
        table_cls.merge_attrs(th_sortable_cls())
    } else {
        table_cls
    };

    th_view(a![
        class![C.select_none, C.cursor_pointer, C.font_semibold],
        mouse_ev(Ev::Click, move |_| SortBy(sort_by)),
        label,
        if is_active {
            paging::dir_toggle_view(dir, class![C.w_5, C.h_4, C.inline, C.ml_1, C.text_blue_500])
        } else {
            empty![]
        }
    ])
    .merge_attrs(table_cls)
}
