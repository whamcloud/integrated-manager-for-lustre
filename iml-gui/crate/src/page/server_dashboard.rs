use crate::{
    components::grafana_chart::{self, ServerDashboardChart, IML_METRICS_DASHBOARD_ID, IML_METRICS_DASHBOARD_NAME},
    Msg,
};
use iml_wire_types::warp_drive::ArcCache;
use seed::prelude::*;

#[derive(Default)]
pub struct Model {
    pub host_name: String,
}

pub fn view(_: &ArcCache, model: &Model) -> impl View<Msg> {
    vec![
        grafana_chart::view(
            IML_METRICS_DASHBOARD_ID,
            IML_METRICS_DASHBOARD_NAME,
            "Read/Write Bandwidth",
            ServerDashboardChart {
                org_id: 1,
                refresh: "10s",
                var_host_name: &model.host_name,
                panel_id: 6,
            },
        ),
        grafana_chart::view(
            IML_METRICS_DASHBOARD_ID,
            IML_METRICS_DASHBOARD_NAME,
            "Memory Usage",
            ServerDashboardChart {
                org_id: 1,
                refresh: "10s",
                var_host_name: &model.host_name,
                panel_id: 8,
            },
        ),
        grafana_chart::view(
            IML_METRICS_DASHBOARD_ID,
            IML_METRICS_DASHBOARD_NAME,
            "CPU Usage",
            ServerDashboardChart {
                org_id: 1,
                refresh: "10s",
                var_host_name: &model.host_name,
                panel_id: 10,
            },
        ),
    ]
}
