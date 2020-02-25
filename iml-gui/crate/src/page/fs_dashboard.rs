use crate::{
    components::{
        charts::fs_usage,
        grafana_chart::{self, FsDashboardChart, IML_METRICS_DASHBOARD_ID, IML_METRICS_DASHBOARD_NAME},
    },
    GMsg,
};
use seed::prelude::*;

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
    vec![
        fs_usage::view(&model.fs_usage),
        grafana_chart::view(
            IML_METRICS_DASHBOARD_ID,
            IML_METRICS_DASHBOARD_NAME,
            "Objects Used",
            FsDashboardChart {
                org_id: 1,
                refresh: "10s",
                var_fs_name: &model.fs_name,
                panel_id: 2,
            },
        ),
        grafana_chart::view(
            IML_METRICS_DASHBOARD_ID,
            IML_METRICS_DASHBOARD_NAME,
            "Files Used",
            FsDashboardChart {
                org_id: 1,
                refresh: "10s",
                var_fs_name: &model.fs_name,
                panel_id: 4,
            },
        ),
    ]
}

pub fn init(orders: &mut impl Orders<Msg, GMsg>) {
    orders.proxy(Msg::FsUsage).send_msg(fs_usage::Msg::FetchData);
}
