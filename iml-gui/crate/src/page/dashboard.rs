use crate::{
    components::{
        chart::fs_usage,
        dashboard::{dashboard_container, dashboard_fs_usage},
        datepicker::datepicker,
        grafana_chart::{self, create_chart_params, IML_METRICS_DASHBOARD_ID, IML_METRICS_DASHBOARD_NAME},
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

fn performance_container<T>(bw_id: u16, iops_id: u16) -> Node<T> {
    let chart = grafana_chart::view(
        IML_METRICS_DASHBOARD_ID,
        IML_METRICS_DASHBOARD_NAME,
        vec![
            DashboardChart {
                org_id: 1,
                refresh: "10s",
                panel_id: bw_id,
            },
            DashboardChart {
                org_id: 1,
                refresh: "10s",
                panel_id: iops_id,
            },
        ],
        "38%",
    );

    div![
        class![C.h_80, C.px_2],
        div![
            class![C.text_center],
            p![
                class![
                    C.inline_block,
                    C.bg_throughput_background,
                    C.rounded_full,
                    C.px_2,
                    C.text_xs,
                    C.text_white
                ],
                "Throughput"
            ],
        ],
        chart[0].clone(),
        div![
            class![C.text_center],
            p![
                class![
                    C.inline_block,
                    C.bg_green_400,
                    C.rounded_full,
                    C.px_2,
                    C.text_xs,
                    C.text_white
                ],
                "IOPS"
            ],
        ],
        chart[1].clone(),
        datepicker(),
    ]
}

pub fn view<T: 'static>(model: &Model) -> Node<T> {
    div![
        class![C.grid, C.lg__grid_cols_2, C.gap_6],
        vec![
            dashboard_fs_usage::view(&model.fs_usage),
            dashboard_container::view("I/O Performance", performance_container(18, 20)),
            dashboard_container::view(
                "OST Balance",
                div![
                    class![C.h_80, C.p_2],
                    grafana_chart::view(
                        IML_METRICS_DASHBOARD_ID,
                        IML_METRICS_DASHBOARD_NAME,
                        vec![DashboardChart {
                            org_id: 1,
                            refresh: "10s",
                            panel_id: 26,
                        }],
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
                        vec![DashboardChart {
                            org_id: 1,
                            refresh: "10s",
                            panel_id: 34,
                        }],
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
