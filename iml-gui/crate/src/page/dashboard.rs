use crate::{
    components::{
        chart::fs_usage,
        dashboard::{dashboard_container, dashboard_fs_usage},
        grafana_chart::{self, DashboardChart, IML_METRICS_DASHBOARD_ID, IML_METRICS_DASHBOARD_NAME},
    },
    generated::css_classes::C,
    GMsg,
};
use seed::{class, div, prelude::*, *};

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

fn performance_container<T>(performance_chart: Vec<Node<T>>) -> Node<T> {
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
        performance_chart[0].clone(),
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
        performance_chart[1].clone(),
        div![
            class![C.text_center],
            div![
                class![C.inline_block, C.rounded_full, C.px_2, C.text_gray_400, C.text_xs,],
                button![
                    class![C.inline_block, C.bg_blue_500, C.px_6, C.rounded_l_full, C.text_white,],
                    "Day",
                ],
                button![
                    class![
                        C.inline_block,
                        C.bg_gray_200,
                        C.px_6,
                        C.border_l,
                        C.border_r,
                        C.border_white,
                        C.border_l_2,
                        C.border_r_2,
                    ],
                    "2 Days",
                ],
                button![class![C.inline_block, C.px_6, C.bg_gray_200, C.rounded_r_full,], "Week",],
            ],
        ],
    ]
}

pub fn view<T: 'static>(model: &Model) -> Node<T> {
    let write_performance_chart = grafana_chart::view(
        IML_METRICS_DASHBOARD_ID,
        IML_METRICS_DASHBOARD_NAME,
        vec![
            DashboardChart {
                org_id: 1,
                refresh: "10s",
                panel_id: 18,
            },
            DashboardChart {
                org_id: 1,
                refresh: "10s",
                panel_id: 20,
            },
        ],
        "38%",
    );

    let read_performance_chart = grafana_chart::view(
        IML_METRICS_DASHBOARD_ID,
        IML_METRICS_DASHBOARD_NAME,
        vec![
            DashboardChart {
                org_id: 1,
                refresh: "10s",
                panel_id: 24,
            },
            DashboardChart {
                org_id: 1,
                refresh: "10s",
                panel_id: 22,
            },
        ],
        "38%",
    );

    div![
        class![C.grid, C.grid_cols_2, C.gap_6],
        vec![
            dashboard_fs_usage::view(&model.fs_usage),
            dashboard_container::view("Write Performance", performance_container(write_performance_chart)),
            dashboard_container::view("Read Performance", performance_container(read_performance_chart)),
            dashboard_container::view(
                "Objects Used",
                div![
                    class![C.h_80, C.p_2],
                    grafana_chart::view(
                        IML_METRICS_DASHBOARD_ID,
                        IML_METRICS_DASHBOARD_NAME,
                        vec![DashboardChart {
                            org_id: 1,
                            refresh: "10s",
                            panel_id: 2,
                        }],
                        "90%",
                    )
                ]
            ),
            dashboard_container::view(
                "Files Used",
                div![
                    class![C.h_80, C.p_2],
                    grafana_chart::view(
                        IML_METRICS_DASHBOARD_ID,
                        IML_METRICS_DASHBOARD_NAME,
                        vec![DashboardChart {
                            org_id: 1,
                            refresh: "10s",
                            panel_id: 4,
                        }],
                        "90%",
                    )
                ]
            ),
        ]
    ]
}

pub fn init(orders: &mut impl Orders<Msg, GMsg>) {
    orders.proxy(Msg::FsUsage).send_msg(fs_usage::Msg::FetchData);
}
