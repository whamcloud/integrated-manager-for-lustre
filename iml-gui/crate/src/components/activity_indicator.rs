use crate::{components::font_awesome, generated::css_classes::C};
use iml_wire_types::{Alert, AlertSeverity};
use seed::{prelude::*, *};
use std::collections::{HashMap, HashSet};

pub fn update_activity_health(
    active_alert: &HashMap<u32, Alert>,
) -> ActivityHealth {
    let xs = active_alert
        .iter()
        .filter(|(_, x)| match x.severity {
            AlertSeverity::WARNING | AlertSeverity::ERROR => true,
            _ => false,
        })
        .map(|(_, x)| &x.severity)
        .collect::<Vec<_>>();

    let count = xs.len();

    let s = xs.into_iter().collect::<HashSet<&AlertSeverity>>();

    let mut health = AlertSeverity::INFO;

    if s.contains(&AlertSeverity::ERROR) {
        health = AlertSeverity::ERROR
    } else if s.contains(&AlertSeverity::WARNING) {
        health = AlertSeverity::WARNING;
    }

    ActivityHealth {
        health,
        count,
    }
}

pub struct ActivityHealth {
    pub count: usize,
    pub health: iml_wire_types::AlertSeverity,
}

pub fn activity_indicator<T>(activity_health: &ActivityHealth) -> Node<T> {
    span![
        class![C.mr_3, C.text_green_500 => activity_health.health == AlertSeverity::INFO,
                            C.text_yellow_500 => activity_health.health == AlertSeverity::WARNING,
                            C.text_red_500 => activity_health.health == AlertSeverity::ERROR],
        font_awesome(class![C.h_6, C.w_6, C.mr_1, C.inline], "bell"),
        sup![activity_health.count.to_string()]
    ]
}
