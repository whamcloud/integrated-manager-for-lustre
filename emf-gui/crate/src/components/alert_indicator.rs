// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    components::{attrs, font_awesome_outline, tooltip, Placement},
    generated::css_classes::C,
};
use emf_wire_types::{warp_drive::ArcValuesExt, Alert, AlertSeverity, ToCompositeId};
use im::HashMap;
use seed::{prelude::*, *};
use std::{cmp::max, collections::BTreeSet, iter::FromIterator, sync::Arc};

pub(crate) fn alert_indicator<T>(
    alerts: &HashMap<i32, Arc<Alert>>,
    x: &dyn ToCompositeId,
    compact: bool,
    tt_placement: Placement,
) -> Node<T> {
    let composite_id = x.composite_id();

    let alerts: Vec<&Alert> = alerts
        .arc_values()
        .filter_map(|x| {
            let xs = x.affected_composite_ids.as_ref()?;

            BTreeSet::from_iter(xs).get(&composite_id)?;

            Some(x)
        })
        .collect();

    if compact && alerts.is_empty() {
        return empty![];
    }

    let count = alerts.len();

    let msg = if count == 0 {
        "No Alerts".into()
    } else if count == 1 {
        alerts[0].message.clone()
    } else {
        format!("{} Alerts", alerts.len())
    };

    let health = alerts.into_iter().map(|x| x.severity).fold(AlertSeverity::INFO, max);

    let cls = if health == AlertSeverity::INFO {
        C.text_blue_500
    } else if health == AlertSeverity::WARNING {
        C.text_yellow_500
    } else {
        C.text_red_500
    };

    let icon = font_awesome_outline(class![cls, C.inline, C.h_4, C.w_4], "bell");

    if compact {
        span![
            class![C.inline_block],
            span![attrs::container(), icon, tooltip::view(&msg, tt_placement)],
            sup![class![cls], count.to_string()]
        ]
    } else {
        span![icon, span![class![C.ml_1], &msg]]
    }
}
