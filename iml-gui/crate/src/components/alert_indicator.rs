// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    components::{attrs, font_awesome_outline, popover, tooltip, Placement},
    generated::css_classes::C,
};
use im::HashMap;
use iml_wire_types::{warp_drive::ArcValuesExt, Alert, AlertSeverity, ToCompositeId};
use seed::{prelude::*, *};
use std::{collections::BTreeSet, iter::FromIterator, sync::Arc};

pub(crate) fn alert_indicator<T>(
    all_alerts: &HashMap<i32, Arc<Alert>>,
    x: &dyn ToCompositeId,
    compact: bool,
    tt_placement: Placement,
) -> Node<T> {
    let composite_id = x.composite_id();

    let mut alerts = all_alerts
        .arc_values()
        .filter_map(|x| {
            let xs = x.affected_composite_ids.as_ref()?;

            BTreeSet::from_iter(xs).get(&composite_id)?;

            Some(x)
        })
        .collect::<Vec<_>>();

    if compact && alerts.is_empty() {
        return empty![];
    }

    // Put the most severe alerts first:
    alerts.sort_unstable_by(|a, b| b.severity.cmp(&a.severity));

    let health = alerts.get(0).map(|a| a.severity).unwrap_or(AlertSeverity::INFO);
    let cls = if health == AlertSeverity::INFO {
        C.text_blue_500
    } else if health == AlertSeverity::WARNING {
        C.text_yellow_500
    } else {
        C.text_red_500
    };

    let icon = font_awesome_outline(class![cls, C.inline, C.h_4, C.w_4], "bell");

    let count = alerts.len();

    let txt = if count == 0 {
        "No Alerts".into()
    } else if count == 1 {
        alerts[0].message.clone()
    } else {
        format!("{} Alerts", alerts.len())
    };

    let mut el = if compact {
        span![
            class![C.inline_block],
            attrs::container(),
            icon,
            tooltip::view(&txt, tt_placement),
            sup![class![cls], count.to_string()]
        ]
    } else {
        span![icon, attrs::container(), span![class![C.ml_1], &txt]]
    };

    if count > 1 {
        let pop = popover::view(
            popover::content_view(ul![
                class![C.list_disc, C.px_4, C.whitespace_no_wrap, C.text_left],
                alerts.into_iter().map(|a| li![&a.message])
            ]),
            Placement::Bottom,
        );
        el.add_child(pop)
            .add_class(C.cursor_pointer)
            .add_class(C.outline_none)
            .add_attr(At::TabIndex.as_str(), 0);
    }

    el
}
