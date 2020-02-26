use crate::{
    components::{
        dashboard::dashboard_container,
        grafana_chart::{self, ServerDashboardChart, IML_METRICS_DASHBOARD_ID, IML_METRICS_DASHBOARD_NAME},
    },
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
        dashboard_container::view(
            "Read/Write Bandwidth",
            grafana_chart::view(
                IML_METRICS_DASHBOARD_ID,
                IML_METRICS_DASHBOARD_NAME,
                vec![ServerDashboardChart {
                    org_id: 1,
                    refresh: "10s",
                    var_host_name: &model.host_name,
                    panel_id: 6,
                }],
                "90%",
            ),
        ),
        dashboard_container::view(
            "Memory Usage",
            grafana_chart::view(
                IML_METRICS_DASHBOARD_ID,
                IML_METRICS_DASHBOARD_NAME,
                vec![ServerDashboardChart {
                    org_id: 1,
                    refresh: "10s",
                    var_host_name: &model.host_name,
                    panel_id: 8,
                }],
                "90%",
            ),
        ),
        dashboard_container::view(
            "CPU Usage",
            grafana_chart::view(
                IML_METRICS_DASHBOARD_ID,
                IML_METRICS_DASHBOARD_NAME,
                vec![ServerDashboardChart {
                    org_id: 1,
                    refresh: "10s",
                    var_host_name: &model.host_name,
                    panel_id: 10,
                }],
                "90%",
            ),
        ),
    ]
}
