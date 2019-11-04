// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    action_dropdown::{action_dropdown, dropdown_header},
    model::{has_lock, Record},
};
use iml_utils::{dispatch_custom_event, Locks, WatchState};
use iml_wire_types::HsmControlParam;
use seed::{
    a, class,
    events::{mouse_ev, Ev},
    li,
    prelude::*,
};
use std::{collections::HashMap, iter};

/// A record and HsmControlParam are triggered when an option is selected.
#[derive(serde::Serialize, Clone, Debug)]
pub struct RecordAndHsmControlParam {
    pub record: Record,
    pub hsm_control_param: HsmControlParam,
}

#[derive(serde::Deserialize, serde::Serialize, Debug, Clone)]
pub struct HsmData {
    pub record: Record,
    pub locks: Locks,
    pub tooltip_placement: Option<iml_tooltip::TooltipPlacement>,
    pub tooltip_size: Option<iml_tooltip::TooltipSize>,
}

#[derive(Debug)]
pub struct Model {
    pub id: u32,
    pub watching: WatchState,
    pub is_locked: bool,
    pub record: Record,
    pub locks: Locks,
    pub tooltip: iml_tooltip::Model,
    pub destroyed: bool,
}

#[derive(Clone)]
pub enum Msg {
    WatchChange,
    SetLocks(Locks),
    SetRecord(Record),
    ActionClicked(RecordAndHsmControlParam),
    Destroy,
}

/// The sole source of updating the model
pub fn update(msg: Msg, model: &mut Model, _orders: &mut impl Orders<Msg>) {
    if model.destroyed {
        return;
    }

    match msg {
        Msg::SetRecord(record) => {
            model.is_locked = has_lock(&model.locks, &record);
            model.record = record;
        }
        Msg::WatchChange => {
            if model.watching.should_update() {
                model.watching.update()
            }
        }
        Msg::SetLocks(locks) => {
            model.is_locked = has_lock(&locks, &model.record);
            model.locks = locks;
        }
        Msg::ActionClicked(x) => {
            dispatch_custom_event("hsm_action_selected", &x);
        }
        Msg::Destroy => {
            model.destroyed = true;
            model.locks = HashMap::new();
        }
    };
}

pub fn get_record_els_from_hsm_control_params(
    record: &Record,
    hsm_control_params: &[HsmControlParam],
    tooltip_config: &iml_tooltip::Model,
    update_fn: fn(RecordAndHsmControlParam) -> Msg,
) -> Vec<Node<Msg>> {
    let ys = hsm_control_params.into_iter().map(|y| {
        let x = RecordAndHsmControlParam {
            record: record.clone(),
            hsm_control_param: y.clone(),
        };

        li![
            class!["tooltip-container", "tooltip-hover"],
            a![&y.verb],
            iml_tooltip::tooltip(&y.long_description, tooltip_config),
            mouse_ev(Ev::Click, move |_| { update_fn(x.clone()) }),
        ]
    });

    iter::once(dropdown_header(&record.label))
        .chain(ys)
        .collect()
}

pub fn view(model: &Model) -> Node<Msg> {
    if model.destroyed {
        return seed::empty();
    }

    let hsm_control_params = match model.record.hsm_control_params {
        Some(ref x) if !x.is_empty() => x,
        _ => {
            return action_dropdown(model.watching.is_open(), model.is_locked, vec![]);
        }
    };

    if model.is_locked {
        return action_dropdown(model.watching.is_open(), model.is_locked, vec![]);
    }

    let record_els = get_record_els_from_hsm_control_params(
        &model.record,
        &hsm_control_params,
        &model.tooltip,
        Msg::ActionClicked,
    );

    let mut el = action_dropdown(model.watching.is_open(), model.is_locked, record_els);
    el.add_listener(simple_ev(Ev::Click, Msg::WatchChange));
    el
}
