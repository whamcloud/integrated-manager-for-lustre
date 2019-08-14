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

pub fn convert_ms_to_unit(unit: Unit, val: u64) -> u64 {
    match unit {
        Unit::Days => val / 24 / 60 / 60 / 1000,
        Unit::Hours => val / 60 / 60 / 1000,
        Unit::Minutes => val / 60 / 1000,
        Unit::Seconds => val / 1000,
    }
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

    input = input
        .add_class("form-control")
        .add_attrs(attrs! {
            At::Type => "number",
            At::Min => "1",
            At::Max => MAX_SAFE_INTEGER
        })
        .add_listener(raw_ev(Ev::Input, Msg::InputChange));

    if let Some(x) = model.value {
        input = input.add_attr(At::Value.as_str(), x);
    } else {
        input = input.add_attr(At::Value.as_str(), "");
    }

    if model.disabled {
        input = input.add_attr(At::Disabled.as_str(), true);
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

    let btn = bs_dropdown::btn(model.unit.to_string()).add_attrs(attrs);

    let mut dropdown = bs_dropdown::wrapper(
        class![bs_input::INPUT_GROUP_BTN],
        open,
        vec![
            btn,
            bs_dropdown::menu(items).add_class(bs_dropdown::DROPDOWN_MENU_RIGHT),
        ],
    );

    dropdown = if !open && !model.disabled {
        dropdown.add_listener(mouse_ev(Ev::Click, move |_| Msg::WatchChange))
    } else {
        dropdown
    };

    vec![input, el, dropdown]
}
