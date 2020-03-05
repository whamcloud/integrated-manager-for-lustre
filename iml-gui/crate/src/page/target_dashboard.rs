use crate::{
    components::{
        dashboard::{dashboard_container, performance_container},
        grafana_chart::{self, create_chart_params, IML_METRICS_DASHBOARD_ID, IML_METRICS_DASHBOARD_NAME},
    },
    generated::css_classes::C,
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
            Self::OstDashboard
        } else {
            Self::MdtDashboard
        }
    }
}

pub fn view(_: &ArcCache, model: &Model) -> impl View<Msg> {
    let dashboard_type: TargetDashboard = (model.target_name.as_str()).into();

    div![
        class![C.grid, C.lg__grid_cols_2, C.gap_6],
        match dashboard_type {
            TargetDashboard::MdtDashboard => vec![
                dashboard_container::view(
                    "Metadata Operations",
                    div![
                        class![C.h_80, C.p_2],
                        grafana_chart::view(
                            IML_METRICS_DASHBOARD_ID,
                            IML_METRICS_DASHBOARD_NAME,
                            create_chart_params(37, vec![("target_name", &model.target_name)]),
                            "90%",
                        ),
                    ],
                ),
                dashboard_container::view(
                    "Space Usage",
                    div![
                        class![C.h_80, C.p_2],
                        grafana_chart::view(
                            IML_METRICS_DASHBOARD_ID,
                            IML_METRICS_DASHBOARD_NAME,
                            create_chart_params(14, vec![("target_name", &model.target_name)]),
                            "90%",
                        ),
                    ],
                ),
                dashboard_container::view(
                    "File Usage",
                    div![
                        class![C.h_80, C.p_2],
                        grafana_chart::view(
                            IML_METRICS_DASHBOARD_ID,
                            IML_METRICS_DASHBOARD_NAME,
                            create_chart_params(16, vec![("target_name", &model.target_name)]),
                            "90%",
                        ),
                    ],
                )
            ],
            TargetDashboard::OstDashboard => vec![
                dashboard_container::view(
                    "I/O Performance",
                    performance_container(39, 38, vec![("target_name", &model.target_name)]),
                ),
                dashboard_container::view(
                    "Space Usage",
                    div![
                        class![C.h_80, C.p_2],
                        grafana_chart::view(
                            IML_METRICS_DASHBOARD_ID,
                            IML_METRICS_DASHBOARD_NAME,
                            create_chart_params(14, vec![("target_name", &model.target_name)]),
                            "90%",
                        ),
                    ],
                ),
                dashboard_container::view(
                    "Object Usage",
                    div![
                        class![C.h_80, C.p_2],
                        grafana_chart::view(
                            IML_METRICS_DASHBOARD_ID,
                            IML_METRICS_DASHBOARD_NAME,
                            create_chart_params(16, vec![("target_name", &model.target_name)]),
                            "90%",
                        ),
                    ],
                )
            ],
        }
    ]
}
