// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::GMsg;
use emf_wire_types::Session;
use seed::prelude::*;

pub mod report;

#[derive(Default, Debug)]
pub struct Model {
    report: report::Model,
}

#[derive(Clone, Debug)]
pub enum Msg {
    Report(report::Msg),
}

pub fn view(model: &Model, session: Option<&Session>) -> impl View<Msg> {
    report::view(&model.report, session).map_msg(Msg::Report)
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::Report(m) => report::update(m, &mut model.report, &mut orders.proxy(Msg::Report)),
    }
}

pub fn init(model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    report::init(&mut model.report, &mut orders.proxy(Msg::Report));
}
