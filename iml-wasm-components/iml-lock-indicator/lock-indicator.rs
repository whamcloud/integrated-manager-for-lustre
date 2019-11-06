// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use bootstrap_components::{
    bs_panel::{panel, panel_body, panel_heading},
    popover,
};
use iml_tooltip::{tooltip, TooltipPlacement, TooltipSize};
use iml_utils::Locks;
use iml_utils::WatchState;
use iml_wire_types::{CompositeId, LockChange, LockType};
use seed::{class, div, events::mouse_ev, i, li, prelude::*, span, ul};
use std::collections::HashSet;

fn get_locks<'a>(
    x: CompositeId,
    locks: &'a Locks,
) -> Option<(HashSet<&'a LockChange>, HashSet<&'a LockChange>)> {
    locks
        .get(&x.to_string())
        .map(|xs| xs.iter().partition(|x| x.lock_type == LockType::Write))
}

fn get_tooltip_message(
    write_locks: &HashSet<&LockChange>,
    read_locks: &HashSet<&LockChange>,
) -> String {
    format!(
        "Read locks: {}, Write locks: {}. Click to view details",
        read_locks.len(),
        write_locks.len()
    )
}

#[derive(Debug, Clone)]
pub struct LockIndicatorState(pub u32, pub WatchState);

fn lock_panel<T>(title: &'static str, locks: &HashSet<&LockChange>) -> Node<T> {
    if locks.is_empty() {
        seed::empty()
    } else {
        let mut items: Vec<&String> = locks.iter().map(|x| &x.description).collect();

        items.sort_unstable();

        panel(vec![
            panel_heading(Node::new_text(title)),
            panel_body(ul![items.iter().map(|x| li![x])]),
        ])
    }
}

pub fn lock_indicator(
    id: u32,
    open: bool,
    composite_id: CompositeId,
    locks: &Locks,
) -> Node<LockIndicatorState> {
    match get_locks(composite_id, &locks) {
        Some((write_locks, read_locks)) => {
            let mut i = i![class!["fa", "fa-lock"]];

            if !open {
                i.add_listener(mouse_ev(Ev::Click, move |_| {
                    LockIndicatorState(id, WatchState::Watching)
                }));
            };

            span![
                class!["job-status", "tooltip-container", "tooltip-hover"],
                i,
                popover::wrapper(
                    open,
                    &bootstrap_components::BOTTOM,
                    vec![
                        popover::title(Node::new_text("Active Locks")),
                        popover::content(div![
                            lock_panel("Read Locks", &read_locks),
                            lock_panel("Write Locks", &write_locks)
                        ])
                    ]
                ),
                tooltip(
                    &get_tooltip_message(&write_locks, &read_locks),
                    &iml_tooltip::Model {
                        placement: TooltipPlacement::Right,
                        size: TooltipSize::Large,
                        ..Default::default()
                    }
                )
            ]
        }
        None => seed::empty(),
    }
}
