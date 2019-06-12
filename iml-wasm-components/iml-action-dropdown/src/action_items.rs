// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    action_dropdown::{self, dropdown_header},
    dispatch_custom_event::dispatch_custom_event,
    model::{ActionMap, AvailableActionAndRecord, RecordMap},
};
use seed::{a, class, li, prelude::*};
use std::iter;

pub fn get_record_els(
    available_actions: &ActionMap,
    records: &RecordMap,
    flag: &Option<String>,
    tooltip_config: &iml_tooltip::Model,
) -> Vec<El<action_dropdown::Msg>> {
    available_actions
        .iter()
        .flat_map(|(label, xs)| {
            let ys = xs.iter().map(|x| {
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

                        action_dropdown::Msg::Open(false)
                    }),
                    iml_tooltip::tooltip(&x.long_description, tooltip_config)
                ]
            });

            iter::once(dropdown_header(label))
                .chain(ys)
                .chain(iter::once(li![class!["divider"]]))
        })
        .collect()
}
