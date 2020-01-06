use crate::components::{font_awesome_outline, tooltip, Placement};
use crate::generated::css_classes::C;
use im::HashMap;
use iml_wire_types::{Alert, AlertSeverity};
use seed::{prelude::*, *};
use std::cmp::max;

fn get_message(alerts: &[&Alert]) -> String {
    if alerts.is_empty() {
        "No Alerts".into()
    } else if alerts.len() == 1 {
        alerts[0].message.clone()
    } else {
        format!("{} Alerts", alerts.len())
    }
}

pub(crate) fn alert_indicator<T>(
    alerts: &HashMap<u32, Alert>,
    resource_uri: &str,
    compact: bool,
    tt_placement: Placement,
) -> Node<T> {
    let alerts: Vec<&Alert> = alerts
        .values()
        .filter_map(|x| match &x.affected {
            Some(xs) => xs.iter().find(|x| x == &resource_uri).map(|_| x),
            None => None,
        })
        .collect();

    if alerts.is_empty() {
        return empty![];
    }

    let msg = get_message(&alerts);

    let count = alerts.len();

    let health = alerts.into_iter().map(|x| x.severity).fold(AlertSeverity::INFO, max);

    let cls = class![C.text_blue_500 => health == AlertSeverity::INFO,
                            C.text_yellow_500 => health == AlertSeverity::WARNING,
                            C.text_red_500 => health == AlertSeverity::ERROR];

    let el = sup![&cls, count.to_string()];

    let mut icon = font_awesome_outline(cls, "bell");

    icon.add_class(C.w_4).add_class(C.h_4).add_class(C.inline);

    let el = span![
        class![C.inline_block],
        span![tooltip::container(), icon, tooltip::view(&msg, tt_placement)],
        el
    ];

    if compact {
        el
    } else {
        span![el, span![class![C.ml_1], &msg]]
    }
}
