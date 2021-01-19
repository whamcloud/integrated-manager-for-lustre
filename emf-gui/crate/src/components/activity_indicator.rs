// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{components::font_awesome_outline, generated::css_classes::C};
use emf_wire_types::{warp_drive::ArcValuesExt, Alert, AlertSeverity};
use im::HashMap;
use seed::{prelude::*, *};
use std::{cmp::max, sync::Arc};

pub fn update_activity_health(active_alert: &HashMap<i32, Arc<Alert>>) -> ActivityHealth {
    active_alert
        .arc_values()
        .filter(|x: &&Alert| x.severity > AlertSeverity::INFO)
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
        Self {
            health: AlertSeverity::INFO,
            count: 0,
        }
    }
}

pub fn view<T>(activity_health: &ActivityHealth) -> Node<T> {
    div![
        class![C.text_center,
            C.text_green_500 => activity_health.health == AlertSeverity::INFO,
            C.text_yellow_500 => activity_health.health == AlertSeverity::WARNING,
            C.text_red_500 => activity_health.health == AlertSeverity::ERROR
        ],
        font_awesome_outline(class![C.h_8, C.w_8, C.mr_1, C.ml_3, C.inline], "bell"),
        sup![activity_health.count.to_string()]
    ]
}
