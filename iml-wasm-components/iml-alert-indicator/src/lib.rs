// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_popover::{popover, popover_content, popover_title};
use iml_tooltip::{tooltip, TooltipPlacement, TooltipSize};
use iml_wire_types::Alert;
use seed::{class, events::mouse_ev, i, li, prelude::*, span, style, ul};
use std::collections::HashMap;

fn get_message(alerts: &[&Alert]) -> String {
    if alerts.is_empty() {
        "No Issues".into()
    } else if alerts.len() == 1 {
        alerts[0].message.clone()
    } else {
        format!("{} Issues", alerts.len())
    }
}

#[derive(Debug, Copy, Clone)]
pub enum WatchState {
    Watching,
    Open,
    Close,
}

#[derive(Debug, Default)]
pub struct PopoverStates {
    inner: HashMap<u32, WatchState>,
}

fn is_open(x: WatchState) -> bool {
    match x {
        WatchState::Open => true,
        _ => false,
    }
}

fn is_watching(x: WatchState) -> bool {
    match x {
        WatchState::Watching => true,
        _ => false,
    }
}

pub fn handle_window_click(p: &mut PopoverStates) {
    for k in p.get_open() {
        p.update(k, WatchState::Close);
    }

    for k in p.get_watching() {
        p.update(k, WatchState::Open);
    }
}

impl PopoverStates {
    pub fn is_open(&self, id: u32) -> bool {
        self.inner.get(&id).filter(|&&x| is_open(x)).is_some()
    }
    pub fn get_watching(&self) -> Vec<u32> {
        self.inner
            .iter()
            .filter(|(_, &v)| is_watching(v))
            .map(|(k, _)| *k)
            .collect()
    }
    pub fn get_open(&self) -> Vec<u32> {
        self.inner
            .iter()
            .filter(|(_, &v)| is_open(v))
            .map(|(k, _)| *k)
            .collect()
    }
    pub fn update(&mut self, id: u32, state: WatchState) {
        match state {
            WatchState::Watching | WatchState::Open => {
                self.inner.insert(id, state);
            }
            WatchState::Close => {
                self.inner.remove(&id);
            }
        }
    }
}

#[derive(Debug, Clone)]
pub struct AlertIndicatorPopoverState(pub (u32, WatchState));

pub fn alert_indicator(
    alerts: &[Alert],
    id: u32,
    resource_uri: &str,
    open: bool,
) -> El<AlertIndicatorPopoverState> {
    log::debug!("Alerts {:#?}", alerts);

    let alerts: Vec<&Alert> = alerts
        .iter()
        .filter_map(|x| match &x.affected {
            Some(xs) => xs.iter().find(|x| x == &resource_uri).map(|_| x),
            None => None,
        })
        .collect();

    let msg = get_message(&alerts);

    span![
        class!["record-state"],
        span![
            class!["icon-wrap", "tooltip-container", "tooltip-hover"],
            if alerts.is_empty() {
                vec![i![class!["fa", "fa-check-circle"]]]
            } else {
                let mut i = i![class!["fa", "activate-popover", "fa-exclamation-circle"]];

                if !open {
                    i.listeners.push(mouse_ev(Ev::Click, move |_| {
                        AlertIndicatorPopoverState((id, WatchState::Watching))
                    }));
                }

                vec![
                    i,
                    popover(
                        open,
                        iml_popover::Placement::Bottom,
                        vec![
                            popover_title(El::new_text("Alerts")),
                            popover_content(ul![alerts.iter().map(|x| { li![x.message] })]),
                        ],
                    ),
                ]
            },
            tooltip(
                &msg,
                &iml_tooltip::Model {
                    placement: TooltipPlacement::Top,
                    size: if alerts.is_empty() {
                        TooltipSize::Small
                    } else {
                        TooltipSize::Medium
                    },
                    ..Default::default()
                }
            )
        ],
        span![
            class!["state-label"],
            style! { "padding-left" => "10px" },
            &msg
        ]
    ]
}
