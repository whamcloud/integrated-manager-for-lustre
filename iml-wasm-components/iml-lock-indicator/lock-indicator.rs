// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_popover::{popover, popover_content, popover_title};
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

fn panel<T>(els: Vec<El<T>>) -> El<T> {
    div![class!["panel", "panel-default"], els]
}

fn panel_heading<T>(el: El<T>) -> El<T> {
    div![class!["panel-heading"], el]
}

fn panel_body<T>(el: El<T>) -> El<T> {
    div![class!["panel-body"], el]
}

fn lock_panel<T>(title: &str, locks: &HashSet<&LockChange>) -> El<T> {
    if locks.is_empty() {
        seed::empty()
    } else {
        panel(vec![
            panel_heading(El::new_text(title)),
            panel_body(ul![locks.iter().map(|x| li![x.description])]),
        ])
    }
}

pub fn lock_indicator(
    id: u32,
    open: bool,
    composite_id: CompositeId,
    locks: &Locks,
) -> El<LockIndicatorState> {
    match get_locks(composite_id, &locks) {
        Some((write_locks, read_locks)) => {
            let mut i = i![class!["fa", "fa-lock"]];

            if !open {
                i.listeners.push(mouse_ev(Ev::Click, move |_| {
                    LockIndicatorState(id, WatchState::Watching)
                }));
            }

            span![
                class!["job-status", "tooltip-container", "tooltip-hover"],
                i,
                popover(
                    open,
                    &iml_popover::Placement::Bottom,
                    vec![
                        popover_title(El::new_text("Active Locks")),
                        popover_content(div![
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
