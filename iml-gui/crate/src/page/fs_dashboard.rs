use crate::{
    components::{
        chart::fs_usage,
        dashboard::{dashboard_container, dashboard_fs_usage},
        grafana_chart::{self, FsDashboardChart, IML_METRICS_DASHBOARD_ID, IML_METRICS_DASHBOARD_NAME},
    },
    generated::css_classes::C,
    GMsg,
};
use seed::{prelude::*, *};

#[derive(Default)]
pub struct Model {
    pub fs_usage: fs_usage::Model,
    pub fs_name: String,
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

pub fn view<T: 'static>(model: &Model) -> impl View<T> {
    div![
        class![C.grid, C.grid_cols_2, C.gap_6],
        vec![
            dashboard_fs_usage::view(&model.fs_usage),
            dashboard_container::view(
                "Objects Used",
                grafana_chart::view(
                    IML_METRICS_DASHBOARD_ID,
                    IML_METRICS_DASHBOARD_NAME,
                    vec![FsDashboardChart {
                        org_id: 1,
                        refresh: "10s",
                        var_fs_name: &model.fs_name,
                        panel_id: 2,
                    }],
                    "90%",
                )
            ),
            dashboard_container::view(
                "Files Used",
                grafana_chart::view(
                    IML_METRICS_DASHBOARD_ID,
                    IML_METRICS_DASHBOARD_NAME,
                    vec![FsDashboardChart {
                        org_id: 1,
                        refresh: "10s",
                        var_fs_name: &model.fs_name,
                        panel_id: 4,
                    }],
                    "90%",
                )
            ),
        ]
    ]
}

pub fn init(orders: &mut impl Orders<Msg, GMsg>) {
    orders.proxy(Msg::FsUsage).send_msg(fs_usage::Msg::FetchData);
}
