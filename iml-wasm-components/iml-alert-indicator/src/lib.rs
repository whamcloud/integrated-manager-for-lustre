// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use bootstrap_components::popover;
use iml_tooltip::{tooltip, TooltipPlacement, TooltipSize};
use iml_utils::WatchState;
use iml_wire_types::Alert;
use seed::{class, events::mouse_ev, i, li, prelude::*, span, style, ul};

fn get_message(alerts: &[&Alert]) -> String {
    if alerts.is_empty() {
        "No Issues".into()
    } else if alerts.len() == 1 {
        alerts[0].message.clone()
    } else {
        format!("{} Issues", alerts.len())
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
    log::trace!("Alerts {:#?}", alerts);

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
                    popover::wrapper(
                        open,
                        &bootstrap_components::BOTTOM,
                        vec![
                            popover::title(El::new_text("Alerts")),
                            popover::content(ul![alerts.iter().map(|x| { li![x.message] })]),
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
