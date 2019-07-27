// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use bootstrap_components::{bs_button, bs_dropdown, bs_input};
use iml_tooltip::tooltip;
use iml_utils::WatchState;
use seed::{a, attrs, class, input, li, prelude::*};
use std::fmt;
use wasm_bindgen::JsCast;

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
    pub changed: bool,
    pub tooltip_placement: iml_tooltip::TooltipPlacement,
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
            model.unit = unit;
        }
        Msg::WatchChange => model.watching.update(),
        Msg::InputChange(ev) => {
            let target = ev.target().unwrap();
            let input_el = seed::to_input(&target);

            model.value = input_el.value().trim().to_string();

            let validation_message = input_el.validation_message().ok().filter(|x| x != "");

            model.changed = true;
            model.validation_message = validation_message;
        }
    }
}

/// A duration picker
pub fn duration_picker(model: &Model) -> Vec<El<Msg>> {
    let items: Vec<_> = std::iter::once(bs_dropdown::header("Units"))
        .chain(
            vec![Unit::Days, Unit::Hours, Unit::Minutes, Unit::Seconds]
                .into_iter()
                .filter(|x| x != &model.unit)
                .filter(|x| !model.exclude_units.contains(x))
                .map(|x| {
                    li![a![
                        x.to_string(),
                        mouse_ev(Ev::Click, move |_| { Msg::SetUnit(x) })
                    ]]
                }),
        )
        .collect();

    let mut input_attrs = attrs! {
        At::Class => "form-control";
        At::Type => "number"; At::Min => "1";
        At::Value => model.value;
        At::Required => true
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
            placement: model.tooltip_placement.clone(),
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
