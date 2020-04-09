// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::components::command_modal;
use crate::{
    components::{
        chart::fs_usage,
        dashboard::{dashboard_container, dashboard_fs_usage, performance_container},
        datepicker,
        grafana_chart::{self, create_chart_params, no_vars, IML_METRICS_DASHBOARD_ID, IML_METRICS_DASHBOARD_NAME},
    },
    generated::css_classes::C,
    GMsg,
};
use seed::{class, prelude::*, *};

#[derive(Default)]
pub struct Model {
    pub fs_usage: fs_usage::Model,
    pub io_date_picker: datepicker::Model,
    pub lnet_date_picker: datepicker::Model,
}

#[derive(Clone, Debug)]
pub enum Msg {
    Test,
    FsUsage(fs_usage::Msg),
    IoChart(datepicker::Msg),
    LNetChart(datepicker::Msg),
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::Test => {
            // todo remove
            orders.send_g_msg(GMsg::OpenCommandModal(command_modal::Input::Ids(vec![12, 54])));
        }
        Msg::FsUsage(msg) => {
            fs_usage::update(msg, &mut model.fs_usage, &mut orders.proxy(Msg::FsUsage));
        }
        Msg::IoChart(msg) => {
            datepicker::update(msg, &mut model.io_date_picker, &mut orders.proxy(Msg::IoChart));
        }
        Msg::LNetChart(msg) => {
            datepicker::update(msg, &mut model.lnet_date_picker, &mut orders.proxy(Msg::LNetChart));
        }
    }
}

pub fn view(model: &Model) -> Node<Msg> {
    let b = seed::button![
        class![
            C.p_8,
            C.border_2,
            C.rounded_28px,
            C.justify_start,
            C.bg_red_800,
            C.text_white
        ],
        "Test command!",
        simple_ev(Ev::Click, Msg::Test),
    ];
    let c = div![
        class![C.grid, C.lg__grid_cols_2, C.gap_6],
        vec![
            dashboard_fs_usage::view(&model.fs_usage),
            dashboard_container::view(
                "I/O Performance",
                performance_container(
                    &model.io_date_picker,
                    18,
                    20,
                    vec![("from", &model.io_date_picker.from), ("to", &model.io_date_picker.to)]
                )
                .map_msg(Msg::IoChart)
            ),
            dashboard_container::view(
                "OST Balance",
                div![
                    class![C.h_80, C.p_2],
                    grafana_chart::view(
                        IML_METRICS_DASHBOARD_ID,
                        IML_METRICS_DASHBOARD_NAME,
                        create_chart_params(26, "10s", no_vars()),
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
                        create_chart_params(
                            34,
                            "10s",
                            vec![
                                ("from", &model.lnet_date_picker.from),
                                ("to", &model.lnet_date_picker.to)
                            ]
                        ),
                        "90%",
                    ),
                    datepicker::view(&model.lnet_date_picker).map_msg(Msg::LNetChart),
                ]
            ),
        ]
    ];
    div![b, c]
}

pub fn init(orders: &mut impl Orders<Msg, GMsg>) {
    orders.proxy(Msg::FsUsage).send_msg(fs_usage::Msg::FetchData);
}
