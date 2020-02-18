use crate::{
    components::{attrs, font_awesome_outline, tooltip, Placement},
    generated::css_classes::C,
};
use im::HashMap;
use iml_wire_types::{warp_drive::ArcValuesExt, Alert, AlertSeverity, ToCompositeId};
use seed::{prelude::*, *};
use std::{cmp::max, collections::BTreeSet, iter::FromIterator, sync::Arc};

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
    alerts: &HashMap<u32, Arc<Alert>>,
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
        span![attrs::container(), icon, tooltip::view(&msg, tt_placement)],
        el
    ];

    if compact {
        el
    } else {
        span![el, span![class![C.ml_1], &msg]]
    }
}
