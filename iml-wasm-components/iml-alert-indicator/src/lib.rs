// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_popover::{popover, popover_content, popover_title};
use iml_tooltip::{tooltip, TooltipPlacement, TooltipSize};
use iml_wire_types::Alert;
use seed::{class, events::mouse_ev, i, li, prelude::*, span, ul};
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

#[derive(Debug, Default)]
pub struct PopoverStates {
    inner: HashMap<u32, bool>,
}

impl PopoverStates {
    pub fn is_open(&self, id: u32) -> bool {
        *self.inner.get(&id).unwrap_or(&false)
    }
    pub fn update(&mut self, id: u32, state: bool) {
        if state {
            self.inner.insert(id, true);
        } else {
            self.inner.remove(&id);
        }
    }
}

#[derive(Debug, Clone)]
pub struct AlertIndicatorPopoverState(pub (u32, bool));

pub fn alert_indicator(
    alerts: &[Alert],
    id: u32,
    resource_uri: &str,
    open: bool,
) -> El<AlertIndicatorPopoverState> {
    log::debug!("Alerts {:?}", alerts);
    log::debug!("id {}", id);
    log::debug!("resource_uri {}", resource_uri);

    let alerts: Vec<&Alert> = alerts
        .iter()
        .filter_map(|x| match &x.affected {
            Some(xs) => xs.iter().find(|x| x == &resource_uri).map(|_| x),
            None => None,
        })
        .collect();

    span![
        class!["record-state"],
        span![
            class!["icon-wrap", "tooltip-container", "tooltip-hover"],
            if alerts.is_empty() {
                vec![i![class!["fa", "fa-check-circle"]]]
            } else {
                vec![
                    i![
                        class!["fa", "activate-popover", "fa-exclamation-circle"],
                        mouse_ev(Ev::Click, move |_| {
                            AlertIndicatorPopoverState((id, !open))
                        })
                    ],
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
                &get_message(&alerts),
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
        ]
    ]
}
