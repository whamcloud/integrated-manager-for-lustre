// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    components::{
        chart::fs_usage,
        dashboard::{dashboard_container, dashboard_fs_usage, performance_container},
        datepicker::datepicker,
        grafana_chart::{self, create_chart_params, no_vars, IML_METRICS_DASHBOARD_ID, IML_METRICS_DASHBOARD_NAME},
    },
    generated::css_classes::C,
    GMsg,
};
use seed::{class, prelude::*, *};

#[derive(Default)]
pub struct Model {
    pub fs_usage: fs_usage::Model,
}

#[derive(Clone)]
pub enum Msg {
    FsUsage(fs_usage::Msg),
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::FsUsage(msg) => {
            fs_usage::update(msg, &mut model.fs_usage, &mut orders.proxy(Msg::FsUsage));
        }
    }
}

pub fn view<T: 'static>(model: &Model) -> Node<T> {
    div![
        class![C.grid, C.lg__grid_cols_2, C.gap_6],
        vec![
            dashboard_fs_usage::view(&model.fs_usage),
            dashboard_container::view("I/O Performance", performance_container(18, 20, no_vars())),
            dashboard_container::view(
                "OST Balance",
                div![
                    class![C.h_80, C.p_2],
                    grafana_chart::view(
                        IML_METRICS_DASHBOARD_ID,
                        IML_METRICS_DASHBOARD_NAME,
                        create_chart_params(26, no_vars()),
                        "90%",
                    )
                ]
            ),
            dashboard_container::view(
                "LNET Performance",
                div![
                    class![C.h_80, C.p_2],
                    grafana_chart::view(
                        IML_METRICS_DASHBOARD_ID,
                        IML_METRICS_DASHBOARD_NAME,
                        create_chart_params(34, no_vars()),
                        "90%",
                    ),
                    datepicker(),
                ]
            ),
        ]
    ]
}

pub fn init(orders: &mut impl Orders<Msg, GMsg>) {
    orders.proxy(Msg::FsUsage).send_msg(fs_usage::Msg::FetchData);
}
