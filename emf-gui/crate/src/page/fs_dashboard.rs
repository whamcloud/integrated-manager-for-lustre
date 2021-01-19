// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    components::{
        chart::fs_usage,
        dashboard::{dashboard_container, dashboard_fs_usage},
        datepicker,
        grafana_chart::{self, create_chart_params, EMF_METRICS_DASHBOARD_ID, EMF_METRICS_DASHBOARD_NAME},
    },
    generated::css_classes::C,
    GMsg,
};
use seed::{prelude::*, *};

#[derive(Default)]
pub struct Model {
    pub fs_usage: fs_usage::Model,
    pub fs_name: String,
    pub fs_usage_date_picker: datepicker::Model,
    pub mdt_usage_date_picker: datepicker::Model,
}

impl Model {
    pub fn new(fs_name: String) -> Self {
        Self {
            fs_usage: fs_usage::Model::new(fs_name.clone()),
            fs_name,
            ..Default::default()
        }
    }
}

#[derive(Clone, Debug)]
pub enum Msg {
    FsUsage(fs_usage::Msg),
    FsUsageChart(datepicker::Msg),
    MdtUsageChart(datepicker::Msg),
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::FsUsage(msg) => {
            fs_usage::update(msg, &mut model.fs_usage, &mut orders.proxy(Msg::FsUsage));
        }
        Msg::FsUsageChart(msg) => {
            datepicker::update(
                msg,
                &mut model.fs_usage_date_picker,
                &mut orders.proxy(Msg::FsUsageChart),
            );
        }
        Msg::MdtUsageChart(msg) => {
            datepicker::update(
                msg,
                &mut model.mdt_usage_date_picker,
                &mut orders.proxy(Msg::MdtUsageChart),
            );
        }
    }
}

pub fn view(model: &Model) -> Node<Msg> {
    div![
        class![C.grid, C.lg__grid_cols_2, C.gap_6],
        vec![
            dashboard_fs_usage::view(&model.fs_usage),
            dashboard_container::view(
                "Filesystem Usage",
                div![
                    class![C.h_full, C.min_h_80, C.p_2],
                    grafana_chart::view(
                        EMF_METRICS_DASHBOARD_ID,
                        EMF_METRICS_DASHBOARD_NAME,
                        create_chart_params(
                            31,
                            "10s",
                            vec![
                                ("fs_name", &model.fs_name),
                                ("from", &model.fs_usage_date_picker.from),
                                ("to", &model.fs_usage_date_picker.to)
                            ]
                        ),
                        "90%",
                    ),
                    datepicker::view(&model.fs_usage_date_picker).map_msg(Msg::FsUsageChart),
                ],
            ),
            dashboard_container::view(
                "OST Balance",
                div![
                    class![C.h_full, C.min_h_80, C.p_2],
                    grafana_chart::view(
                        EMF_METRICS_DASHBOARD_ID,
                        EMF_METRICS_DASHBOARD_NAME,
                        create_chart_params(35, "10s", vec![("fs_name", &model.fs_name)]),
                        "90%",
                    ),
                ],
            ),
            dashboard_container::view(
                "MDT Usage",
                div![
                    class![C.h_full, C.min_h_80, C.p_2],
                    grafana_chart::view(
                        EMF_METRICS_DASHBOARD_ID,
                        EMF_METRICS_DASHBOARD_NAME,
                        create_chart_params(
                            32,
                            "10s",
                            vec![
                                ("fs_name", &model.fs_name),
                                ("from", &model.mdt_usage_date_picker.from),
                                ("to", &model.mdt_usage_date_picker.to)
                            ]
                        ),
                        "90%",
                    ),
                    datepicker::view(&model.mdt_usage_date_picker).map_msg(Msg::MdtUsageChart),
                ],
            ),
        ]
    ]
}

pub fn init(orders: &mut impl Orders<Msg, GMsg>) {
    orders.proxy(Msg::FsUsage).send_msg(fs_usage::Msg::FetchData);
}
