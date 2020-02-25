use crate::{
    components::grafana_chart::{self, FsDashboardChart, IML_METRICS_DASHBOARD_ID, IML_METRICS_DASHBOARD_NAME},
    Msg,
};
use iml_wire_types::warp_drive::ArcCache;
use seed::prelude::*;

#[derive(Default)]
pub struct Model {
    pub fs_name: String,
}

pub fn view(_: &ArcCache, model: &Model) -> impl View<Msg> {
    vec![
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
