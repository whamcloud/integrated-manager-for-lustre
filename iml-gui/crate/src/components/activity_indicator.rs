use crate::{components::font_awesome, generated::css_classes::C};
use im::HashMap;
use iml_wire_types::{Alert, AlertSeverity};
use seed::{prelude::*, *};
use std::cmp::max;

pub fn update_activity_health(active_alert: &HashMap<u32, Alert>) -> ActivityHealth {
    active_alert
        .values()
        .filter(|x| x.severity > AlertSeverity::INFO)
        .fold(ActivityHealth::default(), |mut acc, x| {
            acc.health = max(acc.health, x.severity);
            acc.count += 1;
            acc
        })
}

#[derive(Debug, Copy, Clone, PartialOrd, PartialEq)]
pub struct ActivityHealth {
    pub health: AlertSeverity,
    pub count: usize,
}

impl Default for ActivityHealth {
    fn default() -> Self {
        ActivityHealth {
            health: AlertSeverity::INFO,
            count: 0,
        }
    }
}

pub fn activity_indicator<T>(activity_health: &ActivityHealth) -> Node<T> {
    span![
        class![C.mr_3, C.text_green_500 => activity_health.health == AlertSeverity::INFO,
                            C.text_yellow_500 => activity_health.health == AlertSeverity::WARNING,
                            C.text_red_500 => activity_health.health == AlertSeverity::ERROR],
        font_awesome(
            class![C.h_6, C.w_6, C.xl__h_6, C.xl__w_6, C.lg__h_5, C.lg__w_5, C.mr_1, C.inline],
            "bell"
        ),
        sup![activity_health.count.to_string()]
    ]
}
