// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::hsm::{contains_hsm_params, RecordAndHsmControlParam};
use crate::tooltip::tooltip_component;
use crate::{ActionMap, AvailableActionAndRecord, Msg, RecordMap, TooltipPlacement, TooltipSize};

use seed::{a, class, li, prelude::*, style};

/// Sends the custom event up to the window, carrying with it the data. Should we move this into its own module?
fn dispatch_custom_event<T>(_type: &str, data: &T)
where
    T: serde::Serialize + ?Sized,
{
    let js_value = JsValue::from_serde(data).expect("Error serializing data");
    let ev = web_sys::CustomEvent::new(_type).unwrap();
    ev.init_custom_event_with_can_bubble_and_cancelable_and_detail(_type, true, true, &js_value);

    let window = web_sys::window().unwrap();
    window.dispatch_event(&ev).unwrap();
}

fn get_record_els_from_hsm_control_params(
    records: &RecordMap,
    tooltip_placement: &TooltipPlacement,
    tooltip_size: &TooltipSize,
) -> Vec<El<Msg>> {
    let record_els: Vec<El<Msg>> = records
        .iter()
        .filter(|(_, x)| x.hsm_control_params != None)
        .flat_map(|(_, x)| {
            let label = x.clone().label;
            let params = x
                .clone()
                .hsm_control_params
                .expect("hsm_control_params are not set.");

            let mut ys: Vec<El<Msg>> = params
                .into_iter()
                .map(|y| {
                    let x2 = x.clone();
                    let y2 = y.clone();
                    let long_description = y2.long_description.as_str();

                    li![
                        class!["tooltip-container", "tooltip-hover"],
                        a![y.verb],
                        mouse_ev(Ev::Click, move |ev| {
                            ev.stop_propagation();
                            ev.prevent_default();
                            dispatch_custom_event(
                                "hsm_action_selected",
                                &RecordAndHsmControlParam {
                                    record: x2.clone(),
                                    hsm_control_param: y.clone(),
                                },
                            );
                            Msg::Open(false)
                        }),
                        tooltip_component(long_description, tooltip_placement, tooltip_size, None)
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
    tooltip_placement: &TooltipPlacement,
    tooltip_size: &TooltipSize,
) -> Vec<El<Msg>> {
    let mut record_els: Vec<El<Msg>> = available_actions
        .iter()
        .flat_map(|(label, xs)| {
            let mut ys: Vec<El<Msg>> = xs
                .iter()
                .map(|x| {
                    let x2 = x.clone();
                    let record = records
                        .get(&x.composite_id)
                        .expect("Could not locate the record label.")
                        .clone();
                    let flag2 = flag.clone();

                    li![
                        class!["tooltip-container", "tooltip-hover"],
                        a![x.verb],
                        mouse_ev(Ev::Click, move |ev| {
                            ev.stop_propagation();
                            ev.prevent_default();
                            dispatch_custom_event(
                                "action_selected",
                                &AvailableActionAndRecord {
                                    available_action: x2.clone(),
                                    record: record.clone(),
                                    flag: flag2.clone(),
                                },
                            );
                            Msg::Open(false)
                        }),
                        tooltip_component(
                            &x.long_description,
                            tooltip_placement,
                            tooltip_size,
                            None
                        )
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
    tooltip_placement: &TooltipPlacement,
    tooltip_size: &TooltipSize,
) -> Vec<El<Msg>> {
    let mut els: Vec<El<Msg>> = Vec::new();
    if contains_hsm_params(records) {
        let mut hsm_els: Vec<El<Msg>> =
            get_record_els_from_hsm_control_params(records, tooltip_placement, tooltip_size);
        els.append(&mut hsm_els);
    }

    if available_actions.len() > 0 {
        let mut action_els = get_record_els_from_available_actions(
            available_actions,
            records,
            flag,
            tooltip_placement,
            tooltip_size,
        );
        els.append(&mut action_els);
    }

    els
}
