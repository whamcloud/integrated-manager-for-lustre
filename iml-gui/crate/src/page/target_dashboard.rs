use crate::{
    components::{
        dashboard::dashboard_container,
        grafana_chart::{self, TargetDashboardChart, IML_METRICS_DASHBOARD_ID, IML_METRICS_DASHBOARD_NAME},
    },
    Msg,
};
use iml_wire_types::warp_drive::ArcCache;
use seed::{prelude::*, *};

#[derive(Default)]
pub struct Model {
    pub target_name: String,
}

pub enum TargetDashboard {
    MdtDashboard,
    OstDashboard,
}

impl From<&str> for TargetDashboard {
    fn from(item: &str) -> Self {
        if item.contains("OST") {
            TargetDashboard::OstDashboard
        } else {
            TargetDashboard::MdtDashboard
        }
    }
}

pub fn view(_: &ArcCache, model: &Model) -> impl View<Msg> {
    let dashboard_type: TargetDashboard = (model.target_name.as_str()).into();

    match dashboard_type {
        TargetDashboard::MdtDashboard => div![
            dashboard_container::view(
                "Metadata Operations",
                grafana_chart::view(
                    IML_METRICS_DASHBOARD_ID,
                    IML_METRICS_DASHBOARD_NAME,
                    vec![TargetDashboardChart {
                        org_id: 1,
                        refresh: "10s",
                        var_target_name: &model.target_name,
                        panel_id: 12,
                    }],
                    "90%",
                )
            ),
            dashboard_container::view(
                "Space Usage",
                grafana_chart::view(
                    IML_METRICS_DASHBOARD_ID,
                    IML_METRICS_DASHBOARD_NAME,
                    vec![TargetDashboardChart {
                        org_id: 1,
                        refresh: "10s",
                        var_target_name: &model.target_name,
                        panel_id: 14,
                    }],
                    "90%",
                )
            ),
            dashboard_container::view(
                "File Usage",
                grafana_chart::view(
                    IML_METRICS_DASHBOARD_ID,
                    IML_METRICS_DASHBOARD_NAME,
                    vec![TargetDashboardChart {
                        org_id: 1,
                        refresh: "10s",
                        var_target_name: &model.target_name,
                        panel_id: 16,
                    }],
                    "90%",
                )
            )
        ],
        TargetDashboard::OstDashboard => div![
            dashboard_container::view(
                "Read/Write Bandwidth",
                grafana_chart::view(
                    IML_METRICS_DASHBOARD_ID,
                    IML_METRICS_DASHBOARD_NAME,
                    vec![TargetDashboardChart {
                        org_id: 1,
                        refresh: "10s",
                        var_target_name: &model.target_name,
                        panel_id: 6,
                    }],
                    "90%",
                )
            ),
            dashboard_container::view(
                "Space Usage",
                grafana_chart::view(
                    IML_METRICS_DASHBOARD_ID,
                    IML_METRICS_DASHBOARD_NAME,
                    vec![TargetDashboardChart {
                        org_id: 1,
                        refresh: "10s",
                        var_target_name: &model.target_name,
                        panel_id: 14,
                    }],
                    "90%",
                )
            ),
            dashboard_container::view(
                "Object Usage",
                grafana_chart::view(
                    IML_METRICS_DASHBOARD_ID,
                    IML_METRICS_DASHBOARD_NAME,
                    vec![TargetDashboardChart {
                        org_id: 1,
                        refresh: "10s",
                        var_target_name: &model.target_name,
                        panel_id: 16,
                    }],
                    "90%",
                )
            )
        ],
    }
}
