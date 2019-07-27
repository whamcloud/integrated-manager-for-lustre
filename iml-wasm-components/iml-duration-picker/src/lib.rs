// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use bootstrap_components::{bs_button, bs_dropdown, bs_input};
use iml_environment::MAX_SAFE_INTEGER;
use iml_tooltip::tooltip;
use iml_utils::WatchState;
use seed::{a, attrs, class, input, li, prelude::*};
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
    pub value: String,
    pub validation_message: Option<String>,
    pub unit: Unit,
    pub watching: WatchState,
    pub exclude_units: Vec<Unit>,
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
            let old_unit = model.unit;
            model.unit = unit;
            if !model.value.is_empty() {
                let old_val = model.value.parse::<u64>();
                if let Ok(val) = old_val {
                    let ms = convert_unit_to_ms(old_unit, val);
                    model.value = convert_ms_to_unit(unit, ms).to_string();
                }
            }
        }
        Msg::WatchChange => model.watching.update(),
        Msg::InputChange(ev) => {
            let target = ev.target().unwrap();
            let input_el = seed::to_input(&target);

            model.value = input_el.value().trim().to_string();

            model.validation_message = input_el.validation_message().ok().filter(|x| x != "");
        }
    }
}

pub fn convert_unit_to_ms(unit: Unit, val: u64) -> u64 {
    match unit {
        Unit::Days => val * 24 * 60 * 60 * 1000,
        Unit::Hours => val * 60 * 60 * 1000,
        Unit::Minutes => val * 60 * 1000,
        Unit::Seconds => val * 1000,
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

pub fn duration_picker(model: &Model) -> Vec<El<Msg>> {
    let items: Vec<_> = std::iter::once(bs_dropdown::header("Units"))
        .chain(
            vec![Unit::Days, Unit::Hours, Unit::Minutes, Unit::Seconds]
                .into_iter()
                .filter(|x| x != &model.unit)
                .filter(|x| !model.exclude_units.contains(x))
                .map(|x| li![a![x.to_string(), simple_ev(Ev::Click, Msg::SetUnit(x))]]),
        )
        .collect();

    let mut input_attrs = attrs! {
        At::Class => "form-control",
        At::Type => "number",
        At::Min => "1",
        At::Max => MAX_SAFE_INTEGER,
        At::Required => true,
        At::Value => model.value,
    };

    let disabled_attrs = if model.disabled {
        attrs! {At::Disabled => true}
    } else {
        attrs! {}
    };

    input_attrs.merge(disabled_attrs.clone());

    let input = input![input_attrs, raw_ev(Ev::Input, Msg::InputChange)];

    let validation_message = &model.validation_message;
    let el = if let (Some(msg), false) = (validation_message, model.disabled) {
        let tt_model = iml_tooltip::Model {
            error_tooltip: true,
            open: true,
            ..Default::default()
        };

        tooltip(&msg, &tt_model)
    } else {
        seed::empty()
    };

    let btn_class = if model.validation_message.is_some() {
        bs_button::BTN_DANGER
    } else {
        bs_button::BTN_DEFAULT
    };

    let mut attrs = class![btn_class];
    attrs.merge(disabled_attrs);

    let open = model.watching.is_open();

    let mut btn = bs_dropdown::btn(&model.unit.to_string());
    btn.attrs.merge(attrs);

    let mut dropdown = bs_dropdown::wrapper(
        class![bs_input::INPUT_GROUP_BTN],
        open,
        vec![
            btn,
            bs_dropdown::menu(items).add_class(bs_dropdown::DROPDOWN_MENU_RIGHT),
        ],
    );

    if !open && !model.disabled {
        dropdown
            .listeners
            .push(mouse_ev(Ev::Click, move |_| Msg::WatchChange));
    }

    vec![input, el, dropdown]
}
