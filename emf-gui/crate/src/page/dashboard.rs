// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    components::{
        chart::fs_usage,
        dashboard::{dashboard_container, dashboard_fs_usage, performance_container},
        datepicker,
        grafana_chart::{self, create_chart_params, no_vars, EMF_METRICS_DASHBOARD_ID, EMF_METRICS_DASHBOARD_NAME},
        sfa_overview,
    },
    generated::css_classes::C,
    GMsg, RecordChange,
};
use emf_wire_types::warp_drive::{ArcCache, ArcRecord, RecordId};
use seed::{class, prelude::*, *};

#[derive(Default)]
pub struct Model {
    pub fs_usage: fs_usage::Model,
    pub io_date_picker: datepicker::Model,
    pub lnet_date_picker: datepicker::Model,
    pub sfa_overview: Option<sfa_overview::Model>,
}

impl RecordChange<Msg> for Model {
    fn update_record(&mut self, record: ArcRecord, cache: &ArcCache, orders: &mut impl Orders<Msg, GMsg>) {
        if let Some(overview) = self.sfa_overview.as_mut() {
            overview.update_record(record, cache, &mut orders.proxy(Msg::SfaOverview));
        }
    }
    fn remove_record(&mut self, id: RecordId, cache: &ArcCache, orders: &mut impl Orders<Msg, GMsg>) {
        if let Some(overview) = self.sfa_overview.as_mut() {
            overview.remove_record(id, cache, &mut orders.proxy(Msg::SfaOverview));
        }
    }
    fn set_records(&mut self, cache: &ArcCache, orders: &mut impl Orders<Msg, GMsg>) {
        if let Some(overview) = self.sfa_overview.as_mut() {
            overview.set_records(cache, &mut orders.proxy(Msg::SfaOverview));
        }
    }
}

#[derive(Clone, Debug)]
pub enum Msg {
    FsUsage(fs_usage::Msg),
    IoChart(datepicker::Msg),
    LNetChart(datepicker::Msg),
    SfaOverview(sfa_overview::Msg),
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::FsUsage(msg) => {
            fs_usage::update(msg, &mut model.fs_usage, &mut orders.proxy(Msg::FsUsage));
        }
        Msg::IoChart(msg) => {
            datepicker::update(msg, &mut model.io_date_picker, &mut orders.proxy(Msg::IoChart));
        }
        Msg::LNetChart(msg) => {
            datepicker::update(msg, &mut model.lnet_date_picker, &mut orders.proxy(Msg::LNetChart));
        }
        Msg::SfaOverview(msg) => {
            if let Some(overview) = model.sfa_overview.as_mut() {
                sfa_overview::update(msg, overview, &mut orders.proxy(Msg::SfaOverview));
            }
        }
    }
}

pub fn view(model: &Model) -> Node<Msg> {
    div![
        class![C.grid, C.lg__grid_cols_2, C.gap_6, C.h_full],
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
            if let Some(overview) = model.sfa_overview.as_ref() {
                sfa_overview::view(overview)
            } else {
                dashboard_container::view(
                    "OST Balance",
                    div![
                        class![C.h_full, C.min_h_80, C.p_2],
                        grafana_chart::view(
                            EMF_METRICS_DASHBOARD_ID,
                            EMF_METRICS_DASHBOARD_NAME,
                            create_chart_params(26, "10s", no_vars()),
                            "90%",
                        )
                    ],
                )
            },
            dashboard_container::view(
                "LNET Performance",
                div![
                    class![C.h_full, C.min_h_80, C.p_2],
                    grafana_chart::view(
                        EMF_METRICS_DASHBOARD_ID,
                        EMF_METRICS_DASHBOARD_NAME,
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
    ]
}

pub fn init(cache: &ArcCache, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    model.set_records(cache, orders);

    if let Some(overview) = model.sfa_overview.as_mut() {
        sfa_overview::init(overview, &mut orders.proxy(Msg::SfaOverview));
    }

    orders.proxy(Msg::FsUsage).send_msg(fs_usage::Msg::FetchData);
}
