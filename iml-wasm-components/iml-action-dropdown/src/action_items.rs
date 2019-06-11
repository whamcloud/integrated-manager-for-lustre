// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    dispatch_custom_event::dispatch_custom_event,
    hsm::{contains_hsm_params, RecordAndHsmControlParam},
    model::{ActionMap, AvailableActionAndRecord},
    Msg, RecordMap,
};
use seed::{a, class, li, prelude::*, style};

fn get_record_els_from_hsm_control_params(
    records: &RecordMap,
    tooltip_config: &iml_tooltip::Model,
) -> Vec<El<Msg>> {
    let record_els: Vec<El<Msg>> = records
        .iter()
        .filter(|(_, x)| x.hsm_control_params.is_some())
        .flat_map(|(_, x)| {
            let label = &x.label;

            let mut ys: Vec<El<Msg>> = x
                .hsm_control_params
                .clone()
                .expect("hsm_control_params are not set.")
                .iter()
                .map(|y| {
                    let record_and_param = RecordAndHsmControlParam {
                        record: x.clone(),
                        hsm_control_param: y.clone(),
                    };

                    li![
                        class!["tooltip-container", "tooltip-hover"],
                        a![&y.verb],
                        mouse_ev(Ev::Click, move |ev| {
                            ev.stop_propagation();
                            ev.prevent_default();
                            dispatch_custom_event("hsm_action_selected", &record_and_param);
                            Msg::Open(false)
                        }),
                        iml_tooltip::tooltip(&y.long_description, tooltip_config)
                    ]
                })
                .collect();

            ys.insert(
                0,
                li![
                    class!["dropdown-header"],
                    style! {"user-select" => "none"},
                    label
                ],
            );

            ys.push(li![class!["divider"]]);

            ys
        })
        .collect();

    record_els
}

fn get_record_els_from_available_actions(
    available_actions: &ActionMap,
    records: &RecordMap,
    flag: &Option<String>,
    tooltip_config: &iml_tooltip::Model,
) -> Vec<El<Msg>> {
    let mut record_els: Vec<El<Msg>> = available_actions
        .iter()
        .flat_map(|(label, xs)| {
            let mut ys: Vec<El<Msg>> = xs
                .iter()
                .map(|x| {
                    let record = records
                        .get(&x.composite_id)
                        .expect("Could not locate the record label.")
                        .clone();

                    let available_action_and_record = AvailableActionAndRecord {
                        available_action: x.clone(),
                        record,
                        flag: flag.clone(),
                    };

                    li![
                        class!["tooltip-container", "tooltip-hover"],
                        a![x.verb],
                        mouse_ev(Ev::Click, move |ev| {
                            ev.stop_propagation();
                            ev.prevent_default();
                            dispatch_custom_event("action_selected", &available_action_and_record);
                            Msg::Open(false)
                        }),
                        iml_tooltip::tooltip(&x.long_description, tooltip_config)
                    ]
                })
                .collect();

            ys.insert(
                0,
                li![
                    class!["dropdown-header"],
                    style! {"user-select" => "none"},
                    label
                ],
            );

            ys.push(li![class!["divider"]]);

            ys
        })
        .collect();

    // The last element will be a divider and is not needed. Remove it.
    record_els.pop();

    record_els
}

/// If there are any hsm_control_params in the records then get the elements from the hsm params and not
/// available actions (which would be empty). Otherwise, get the items using the available actions.
pub fn get_record_els(
    available_actions: &ActionMap,
    records: &RecordMap,
    flag: &Option<String>,
    tooltip_config: &iml_tooltip::Model,
) -> Vec<El<Msg>> {
    let mut els: Vec<El<Msg>> = Vec::new();
    if contains_hsm_params(records) {
        let mut hsm_els: Vec<El<Msg>> =
            get_record_els_from_hsm_control_params(records, tooltip_config);
        els.append(&mut hsm_els);
    }

    if !available_actions.is_empty() {
        let mut action_els =
            get_record_els_from_available_actions(available_actions, records, flag, tooltip_config);
        els.append(&mut action_els);
    }

    els
}
