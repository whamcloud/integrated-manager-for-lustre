// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in th e LICENSE file.

use crate::{
    components::{dropdown, font_awesome, tooltip, Placement},
    environment::MAX_SAFE_INTEGER,
    extensions::{MergeAttrs as _, NodeExt as _},
    generated::css_classes::C,
};
use seed::{prelude::*, *};
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
        Self::Days
    }
}

#[derive(Default, Debug)]
pub struct Model {
    pub disabled: bool,
    pub dropdown: dropdown::Model,
    pub value: Option<u64>,
    pub validation_message: Option<String>,
    pub unit: Unit,
    pub exclude_units: Vec<Unit>,
}

impl Model {
    pub fn value_as_ms(&self) -> Option<u64> {
        self.value.map(|x| match self.unit {
            Unit::Days => x * 24 * 60 * 60 * 1000,
            Unit::Hours => x * 60 * 60 * 1000,
            Unit::Minutes => x * 60 * 1000,
            Unit::Seconds => x * 1000,
        })
    }

    pub fn reset(&mut self) {
        self.value = None;
        self.unit = Unit::default();
    }
}

#[derive(Clone, Debug)]
pub enum Msg {
    SetUnit(Unit),
    InputChange(web_sys::Event),
    Dropdown(dropdown::Msg),
}

pub fn update(msg: Msg, model: &mut Model) {
    match msg {
        Msg::SetUnit(unit) => {
            if let Some(ms) = model.value_as_ms() {
                model.value = Some(convert_ms_to_unit(unit, ms));
            }

            model.unit = unit;
        }
        Msg::InputChange(ev) => {
            let target = ev.target().expect("Couldn't get input element");
            let input_el = seed::to_input(&target);

            let value = input_el.value_as_number();

            model.value = if value.is_nan() { None } else { Some(value as u64) };
            model.validation_message = input_el.validation_message().ok().filter(|x| x != "");
        }
        Msg::Dropdown(msg) => {
            dropdown::update(msg, &mut model.dropdown);
        }
    }
}

pub fn calculate_value_and_unit(model: &mut Model, ms: u64) {
    let interval_opt = convert_ms_to_max_unit(ms);
    if let Some((unit, val)) = interval_opt {
        model.value = Some(val);
        model.unit = unit;
    } else {
        model.value = None;
        model.unit = Unit::Days;
    }
}

pub fn convert_ms_to_unit(unit: Unit, val: u64) -> u64 {
    match unit {
        Unit::Days => val / 24 / 60 / 60 / 1000,
        Unit::Hours => val / 60 / 60 / 1000,
        Unit::Minutes => val / 60 / 1000,
        Unit::Seconds => val / 1000,
    }
}

fn get_unit_value(unit: Unit, val: u64) -> f64 {
    let val = val as f64;
    match unit {
        Unit::Days => val / 24.0 / 60.0 / 60.0 / 1000.0,
        Unit::Hours => val / 60.0 / 60.0 / 1000.0,
        Unit::Minutes => val / 60.0 / 1000.0,
        Unit::Seconds => val / 1000.0,
    }
}

pub fn convert_ms_to_max_unit(val: u64) -> Option<(Unit, u64)> {
    let days = get_unit_value(Unit::Days, val);

    if days.fract() == 0.0 {
        return Some((Unit::Days, days as u64));
    };

    let hours = get_unit_value(Unit::Hours, val);

    if hours.fract() == 0.0 {
        return Some((Unit::Hours, hours as u64));
    };

    let minutes = get_unit_value(Unit::Minutes, val);

    if minutes.fract() == 0.0 {
        return Some((Unit::Minutes, minutes as u64));
    };

    let seconds = get_unit_value(Unit::Seconds, val);

    if seconds.fract() == 0.0 {
        return Some((Unit::Seconds, seconds as u64));
    };

    None
}

fn dropdown_items(unit: Unit, exclude_units: &[Unit]) -> impl View<Msg> {
    vec![Unit::Days, Unit::Hours, Unit::Minutes, Unit::Seconds]
        .into_iter()
        .filter(|x| x != &unit)
        .filter(|x| !exclude_units.contains(x))
        .map(|x| {
            dropdown::item_view(a![x.to_string()])
                .with_listener(ev(Ev::MouseDown, move |ev| {
                    ev.prevent_default();
                    Msg::SetUnit(x)
                }))
                .with_listener(mouse_ev(Ev::Click, move |_| Msg::Dropdown(dropdown::Msg::Close)))
        })
        .collect::<Vec<_>>()
}

pub fn view(model: &Model, mut input: Node<Msg>) -> Node<Msg> {
    let button_cls = class![
        C.text_white,
        C.font_bold,
        C.p_2,
        C.rounded,
        C.rounded_l_none,
        C.w_full,
        C.h_full,
        C.text_sm
    ];

    if let Some(x) = model.value {
        input.add_attr(At::Value.as_str(), x);
    } else {
        input.add_attr(At::Value.as_str(), "");
    }

    if model.disabled {
        input = input.merge_attrs(attrs! {At::Disabled => true});
    }

    let validation_message = &model.validation_message;
    let el = if let (Some(msg), false) = (validation_message, model.disabled) {
        tooltip::base_error_view(msg, Placement::Bottom).merge_attrs(class![C.block])
    } else {
        empty![]
    };

    let mut btn = button![
        button_cls,
        model.unit.to_string(),
        font_awesome(class![C.w_4, C.h_4, C.inline, C.ml_1], "chevron-down"),
        simple_ev(Ev::Blur, Msg::Dropdown(dropdown::Msg::Close)),
        simple_ev(Ev::Click, Msg::Dropdown(dropdown::Msg::Toggle)),
    ];

    if model.validation_message.is_some() {
        input = input.merge_attrs(class![C.border, C.border_red_500, C.border_r_0, C.focus__shadow_none]);
        btn = btn.merge_attrs(class![C.bg_red_500, C.hover__bg_red_700])
    } else {
        btn = btn.merge_attrs(class![C.bg_blue_500, C.hover__bg_blue_700]);
    }

    let open = model.dropdown.is_open();

    input = input.merge_attrs(attrs! {
        At::Type => "number",
        At::Min => "1",
        At::Max => MAX_SAFE_INTEGER
    });
    input.add_listener(ev(Ev::Input, Msg::InputChange));

    div![
        class![C.relative],
        el,
        input,
        div![
            class![C.relative, C.inline_block],
            btn,
            dropdown::wrapper_view(
                Placement::Bottom,
                open,
                dropdown_items(model.unit, &model.exclude_units)
            )
            .merge_attrs(class![C.z_10])
        ]
    ]
}
