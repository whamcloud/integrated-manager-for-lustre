// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    components::{attrs, font_awesome, popover, tooltip, Placement},
    generated::css_classes::C,
};
use im::HashSet;
use iml_wire_types::{warp_drive::Locks, LockChange, LockType, ToCompositeId};
use seed::{prelude::*, *};

pub(crate) fn view<T>(all_locks: &Locks, x: &dyn ToCompositeId) -> Node<T> {
    match all_locks.get(&x.composite_id().to_string()) {
        Some(locks) if !locks.is_empty() => indicator(locks),
        _ => empty![],
    }
}

fn indicator<T>(lcks: &HashSet<LockChange>) -> Node<T> {
    let (rw, ro): (HashSet<&LockChange>, HashSet<&LockChange>) =
        lcks.iter().partition(|l| l.lock_type == LockType::Write);

    let mut tooltip = vec![];
    let mut popup = vec![];

    let rw_c = rw.len();
    if rw_c > 0 {
        if rw_c > 1 {
            tooltip.push(format!("{} write locks", rw_c));
        } else {
            tooltip.push("1 write lock".to_string());
        }
        popup.push(popover::title_view("Write locks"));
        popup.push(popover::content_view(mk_lock_list(&rw)));
    }

    let ro_c = ro.len();
    if ro_c > 0 {
        if ro_c > 1 {
            tooltip.push(format!("{} read locks", ro_c));
        } else {
            tooltip.push("1 read lock".to_string());
        }
        popup.push(popover::title_view("Read locks"));
        popup.push(popover::content_view(mk_lock_list(&ro)));
    }

    span![
        attrs::container(),
        class![C.cursor_pointer, C.outline_none],
        attrs! {At::TabIndex => 0},
        font_awesome(class![C.inline, C.w_4, C.h_4], "lock"),
        tooltip::view(&tooltip.join(", "), Placement::Top),
        popover::view(popup, Placement::Bottom)
    ]
}

fn mk_lock_list<T>(locks: &HashSet<&LockChange>) -> Node<T> {
    let mut items: Vec<&String> = locks.iter().map(|x| &x.description).collect();
    items.sort_unstable();
    ul![
        class![C.list_disc, C.px_4, C.whitespace_no_wrap, C.text_left],
        items.iter().map(|x| li![x])
    ]
}
