use crate::components::{attrs, font_awesome_outline, tooltip, Placement};
use crate::generated::css_classes::C;
use im::HashMap;
use iml_wire_types::{warp_drive::ArcValuesExt, Alert, AlertSeverity, ResourceUri};
use seed::{prelude::*, *};
use std::{cmp::max, sync::Arc};

pub(crate) fn alert_indicator<T>(
    alerts: &HashMap<u32, Arc<Alert>>,
    x: &dyn ResourceUri,
    compact: bool,
    tt_placement: Placement,
) -> Node<T> {
    let alerts: Vec<&Alert> = alerts
        .arc_values()
        .filter_map(|a: &Alert| match &a.affected {
            Some(rs) => rs.iter().find(|r| r == &x.resource_uri()).map(|_| a),
            None => None,
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
