// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_tooltip::tooltip;
use seed::{
    a, attrs, button, class, div, input, li,
    prelude::{mouse_ev, raw_ev, At, El, Ev, Orders, UpdateEl},
    span, style, ul,
};
use std::fmt;

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum Unit {
    Days,
    Hours,
    Minutes,
    Seconds,
}

impl fmt::Display for Unit {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "{:?}", self)
    }
}

impl Default for Unit {
    fn default() -> Self {
        Unit::Days
    }
}

#[derive(Default)]
pub struct Model {
    pub value: String,
    pub validation_message: Option<String>,
    pub unit: Unit,
    pub open: bool,
    pub exclude_units: Vec<Unit>,
}

#[derive(Clone)]
pub enum Msg {
    Open(bool),
    SetUnit(Unit),
    InputChange(web_sys::Event),
    SetValidationMessage(Option<String>),
}

pub fn update<T>(msg: Msg, model: &mut Model, orders: &mut Orders<T>, parent_msg: fn(Msg) -> T) {
    match msg {
        Msg::Open(open) => {
            model.open = open;
        }
        Msg::SetUnit(unit) => {
            model.unit = unit;
            model.open = false;
        }
        Msg::InputChange(ev) => {
            let target = ev.target().unwrap();
            let input_el = seed::to_input(&target);

            model.value = input_el.value().trim().to_string();

            let validation_message = input_el.validation_message().ok().filter(|x| x != "");

            orders.send_msg(parent_msg(Msg::SetValidationMessage(validation_message)));
        }
        Msg::SetValidationMessage(msg) => {
            model.validation_message = msg;
        }
    }
}

fn open_class(open: &bool) -> &str {
    if *open {
        "open"
    } else {
        ""
    }
}

/// A duration picker
pub fn duration_picker<T: Clone>(
    Model {
        open,
        unit,
        value,
        validation_message,
        exclude_units,
    }: &Model,
    msg: fn(Msg) -> T,
) -> El<T> {
    let units = vec![Unit::Days, Unit::Hours, Unit::Minutes, Unit::Seconds];

    let next: bool = !open;

    let mut items = vec![li![
        class!["dropdown-header"],
        style! {"user-select" => "none"},
        "Units"
    ]];

    items.extend(
        units
            .into_iter()
            .filter(|x| x != unit)
            .filter(|x| !exclude_units.contains(x))
            .map(|x| {
                li![a![
                    x.to_string(),
                    mouse_ev(Ev::Click, move |ev| {
                        ev.stop_propagation();
                        ev.prevent_default();
                        msg(Msg::SetUnit(x))
                    })
                ]]
            }),
    );

    let (err_class, el) = if let Some(msg) = validation_message {
        let tt_model = iml_tooltip::Model {
            placement: iml_tooltip::TooltipPlacement::Bottom,
            error_tooltip: true,
            ..Default::default()
        };

        ("has-error", tooltip(&msg, &tt_model))
    } else {
        ("", seed::empty())
    };

    div![
        class!["input-group", "tooltip-container", err_class],
        input![
            attrs! { At::Class => "form-control"; At::Type => "number"; At::Min => "1"; At::Value => value; At::Required => true },
            raw_ev(Ev::Input, move |ev| msg(Msg::InputChange(ev))),
        ],
        el,
        div![
            class!["input-group-btn", "dropdown", open_class(&open)],
            button![
                class!["btn", "btn-default", "dropdown-toggle"],
                unit.to_string(),
                span![class!["caret"], style! {"margin-left" => "3px"}],
                mouse_ev(Ev::Click, move |ev| {
                    ev.stop_propagation();
                    ev.prevent_default();
                    msg(Msg::Open(next))
                })
            ],
            ul![class!["dropdown-menu pull-right"], items]
        ],
    ]
}