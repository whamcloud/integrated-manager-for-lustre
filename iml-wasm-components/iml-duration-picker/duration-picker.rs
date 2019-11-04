// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use bootstrap_components::{bs_button, bs_dropdown, bs_input};
use iml_environment::MAX_SAFE_INTEGER;
use iml_tooltip::tooltip;
use iml_utils::{AddAttrs, WatchState};
use seed::{a, attrs, class, empty, li, prelude::*};
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

#[derive(Default, Debug)]
pub struct Model {
    pub disabled: bool,
    pub value: Option<u64>,
    pub validation_message: Option<String>,
    pub unit: Unit,
    pub watching: WatchState,
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
}

#[derive(Clone, Debug)]
pub enum Msg {
    WatchChange,
    SetUnit(Unit),
    InputChange(web_sys::Event),
}

pub fn update(msg: Msg, model: &mut Model) {
    match msg {
        Msg::SetUnit(unit) => {
            if let Some(ms) = model.value_as_ms() {
                model.value = Some(convert_ms_to_unit(unit, ms));
            }

            model.unit = unit;
        }
        Msg::WatchChange => model.watching.update(),
        Msg::InputChange(ev) => {
            let target = ev.target().unwrap();
            let input_el = seed::to_input(&target);

            let value = input_el.value_as_number();

            model.value = if value.is_nan() {
                None
            } else {
                Some(value as u64)
            };

            model.validation_message = input_el.validation_message().ok().filter(|x| x != "");
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
    let mut result = if days.fract() == 0.0 {
        Some((Unit::Days, days as u64))
    } else {
        None
    };

    if result == None {
        let hours = get_unit_value(Unit::Hours, val);
        result = if hours.fract() == 0.0 {
            Some((Unit::Hours, hours as u64))
        } else {
            None
        };
    }

    if result == None {
        let minutes = get_unit_value(Unit::Minutes, val);
        result = if minutes.fract() == 0.0 {
            Some((Unit::Minutes, minutes as u64))
        } else {
            None
        };
    }

    if result == None {
        let seconds = get_unit_value(Unit::Seconds, val);
        result = if seconds.fract() == 0.0 {
            Some((Unit::Seconds, seconds as u64))
        } else {
            None
        };
    }

    result
}

pub fn duration_picker(model: &Model, mut input: Node<Msg>) -> Vec<Node<Msg>> {
    let items: Vec<Node<_>> = std::iter::once(bs_dropdown::header("Units"))
        .chain(
            vec![Unit::Days, Unit::Hours, Unit::Minutes, Unit::Seconds]
                .into_iter()
                .filter(|x| x != &model.unit)
                .filter(|x| !model.exclude_units.contains(x))
                .map(|x| li![a![x.to_string(), simple_ev(Ev::Click, Msg::SetUnit(x))]]),
        )
        .collect();

    input
        .add_class("form-control")
        .add_attrs(attrs! {
            At::Type => "number",
            At::Min => "1",
            At::Max => MAX_SAFE_INTEGER
        })
        .add_listener(raw_ev(Ev::Input, Msg::InputChange));
    if let Some(x) = model.value {
        input.add_attr(At::Value.as_str(), x);
    } else {
        input.add_attr(At::Value.as_str(), "");
    }

    if model.disabled {
        input.add_attr(At::Disabled.as_str(), true);
    }

    let validation_message = &model.validation_message;
    let el = if let (Some(msg), false) = (validation_message, model.disabled) {
        let tt_model = iml_tooltip::Model {
            error_tooltip: true,
            open: true,
            ..Default::default()
        };

        tooltip(&msg, &tt_model)
    } else {
        empty![]
    };

    let btn_class = if model.validation_message.is_some() {
        bs_button::BTN_DANGER
    } else {
        bs_button::BTN_DEFAULT
    };

    let mut attrs = class![btn_class];

    if model.disabled {
        attrs.add(At::Disabled, true)
    }

    let open = model.watching.is_open();

    let mut btn = bs_dropdown::btn(model.unit.to_string());
    btn.add_attrs(attrs);

    let mut menu = bs_dropdown::menu(items);
    menu.add_class(bs_dropdown::DROPDOWN_MENU_RIGHT);

    let mut dropdown =
        bs_dropdown::wrapper(class![bs_input::INPUT_GROUP_BTN], open, vec![btn, menu]);

    if !open && !model.disabled {
        dropdown.add_listener(mouse_ev(Ev::Click, move |_| Msg::WatchChange));
    };

    vec![input, el, dropdown]
}
