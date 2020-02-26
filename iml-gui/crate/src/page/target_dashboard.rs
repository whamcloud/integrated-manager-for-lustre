use crate::{
    components::grafana_chart::{self, TargetDashboardChart, IML_METRICS_DASHBOARD_ID, IML_METRICS_DASHBOARD_NAME},
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
            grafana_chart::view(
                IML_METRICS_DASHBOARD_ID,
                IML_METRICS_DASHBOARD_NAME,
                "Metadata Operations",
                TargetDashboardChart {
                    org_id: 1,
                    refresh: "10s",
                    var_target_name: &model.target_name,
                    panel_id: 12,
                },
            ),
            grafana_chart::view(
                IML_METRICS_DASHBOARD_ID,
                IML_METRICS_DASHBOARD_NAME,
                "Space Usage",
                TargetDashboardChart {
                    org_id: 1,
                    refresh: "10s",
                    var_target_name: &model.target_name,
                    panel_id: 14,
                },
            ),
            grafana_chart::view(
                IML_METRICS_DASHBOARD_ID,
                IML_METRICS_DASHBOARD_NAME,
                "File Usage",
                TargetDashboardChart {
                    org_id: 1,
                    refresh: "10s",
                    var_target_name: &model.target_name,
                    panel_id: 16,
                },
            )
        ],
        TargetDashboard::OstDashboard => div![
            grafana_chart::view(
                IML_METRICS_DASHBOARD_ID,
                IML_METRICS_DASHBOARD_NAME,
                "Read/Write Bandwidth",
                TargetDashboardChart {
                    org_id: 1,
                    refresh: "10s",
                    var_target_name: &model.target_name,
                    panel_id: 6,
                },
            ),
            grafana_chart::view(
                IML_METRICS_DASHBOARD_ID,
                IML_METRICS_DASHBOARD_NAME,
                "Space Usage",
                TargetDashboardChart {
                    org_id: 1,
                    refresh: "10s",
                    var_target_name: &model.target_name,
                    panel_id: 14,
                },
            ),
            grafana_chart::view(
                IML_METRICS_DASHBOARD_ID,
                IML_METRICS_DASHBOARD_NAME,
                "Object Usage",
                TargetDashboardChart {
                    org_id: 1,
                    refresh: "10s",
                    var_target_name: &model.target_name,
                    panel_id: 16,
                },
            )
        ],
    }
}
