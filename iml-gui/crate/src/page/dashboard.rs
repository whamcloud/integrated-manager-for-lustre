use crate::{
    components::grafana_chart::{self, DashboardChart, IML_METRICS_DASHBOARD_ID, IML_METRICS_DASHBOARD_NAME},
    generated::css_classes::C,
    Msg,
};
use seed::{class, div, prelude::*};

#[derive(Default)]
pub struct Model {}

pub fn view(_: &Model) -> impl View<Msg> {
    div![
        class![C.grid, C.grid_cols_2, C.gap_6],
        vec![
            grafana_chart::view(
                IML_METRICS_DASHBOARD_ID,
                IML_METRICS_DASHBOARD_NAME,
                "Objects Used",
                DashboardChart {
                    org_id: 1,
                    refresh: "10s",
                    panel_id: 2,
                },
            ),
            grafana_chart::view(
                IML_METRICS_DASHBOARD_ID,
                IML_METRICS_DASHBOARD_NAME,
                "Files Used",
                DashboardChart {
                    org_id: 1,
                    refresh: "10s",
                    panel_id: 4,
                },
            ),
        ]
    ]
}
