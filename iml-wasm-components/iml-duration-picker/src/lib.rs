// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_tooltip::tooltip;
use seed::{a, attrs, button, class, div, input, li, prelude::*, span, style, ul};
use std::fmt;

const ESCAPE_KEY: u32 = 27;

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
    pub open: OpenState,
    pub exclude_units: Vec<Unit>,
}

#[derive(Clone)]
pub enum Msg {
    Open(OpenState),
    SetUnit(Unit),
    InputChange(web_sys::Event),
    SetValidationMessage(Option<String>),
    KeyPress(u32),
}

#[derive(Clone, Debug)]
pub enum OpenState {
    Opening,
    Open,
    Close,
}

impl Default for OpenState {
    fn default() -> Self {
        OpenState::Close
    }
}

impl OpenState {
    fn next(&self) -> OpenState {
        match self {
            OpenState::Opening => OpenState::Open,
            OpenState::Open => OpenState::Close,
            OpenState::Close => OpenState::Opening,
        }
    }
}

pub fn update<T: 'static>(
    msg: Msg,
    model: &mut Model,
    orders: &mut Orders<T>,
    parent_msg: fn(Msg) -> T,
) {
    match msg {
        Msg::Open(open) => {
            model.open = open;
        }
        Msg::SetUnit(unit) => {
            model.unit = unit;
            model.open = OpenState::Close;
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
        Msg::KeyPress(code) => {
            if code == ESCAPE_KEY {
                model.open = OpenState::Close;
            }
        }
    }
}

fn open_class(open: &OpenState) -> &str {
    match open {
        OpenState::Close => "",
        _ => "open",
    }
}

/// A duration picker
pub fn duration_picker(
    Model {
        open,
        unit,
        value,
        validation_message,
        exclude_units,
    }: &Model,
) -> El<Msg> {
    let units = vec![Unit::Days, Unit::Hours, Unit::Minutes, Unit::Seconds];

    let next = open.next();

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
                    mouse_ev(Ev::Click, move |_| { Msg::SetUnit(x) })
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
            raw_ev(Ev::Input, Msg::InputChange),
        ],
        el,
        div![
            class!["input-group-btn", "dropdown", open_class(&open)],
            keyboard_ev(Ev::KeyDown, move |ev| { Msg::KeyPress(ev.key_code()) }),
            button![
                class!["btn", "btn-default", "dropdown-toggle"],
                unit.to_string(),
                span![class!["caret"], style! {"margin-left" => "3px"}],
                mouse_ev(Ev::Click, move |ev| {
                    ev.prevent_default();
                    log::info!("button clicked setting open to {:?}", next);
                    Msg::Open(next.clone())
                })
            ],
            ul![class!["dropdown-menu pull-right"], items]
        ],
    ]
}
