use crate::{
    components::{
        dashboard::dashboard_container,
        grafana_chart::{self, create_chart_params, IML_METRICS_DASHBOARD_ID, IML_METRICS_DASHBOARD_NAME},
    },
    generated::css_classes::C,
    Msg,
};
use iml_wire_types::warp_drive::ArcCache;
use seed::{class, div, prelude::*};

#[derive(Default)]
pub struct Model {
    pub host_name: String,
}

pub fn view(_: &ArcCache, model: &Model) -> impl View<Msg> {
    div![
        class![C.grid, C.lg__grid_cols_2, C.gap_6],
        vec![
            dashboard_container::view(
                "Read/Write Bandwidth",
                div![
                    class![C.h_80, C.p_2],
                    grafana_chart::view(
                        IML_METRICS_DASHBOARD_ID,
                        IML_METRICS_DASHBOARD_NAME,
                        create_chart_params(6, vec![("host_name", &model.host_name)]),
                        "90%",
                    ),
                ],
            ),
            dashboard_container::view(
                "CPU Usage",
                div![
                    class![C.h_80, C.p_2],
                    grafana_chart::view(
                        IML_METRICS_DASHBOARD_ID,
                        IML_METRICS_DASHBOARD_NAME,
                        create_chart_params(10, vec![("host_name", &model.host_name)]),
                        "90%",
                    ),
                ],
            ),
            dashboard_container::view(
                "Memory Usage",
                div![
                    class![C.h_80, C.p_2],
                    grafana_chart::view(
                        IML_METRICS_DASHBOARD_ID,
                        IML_METRICS_DASHBOARD_NAME,
                        create_chart_params(8, vec![("host_name", &model.host_name)]),
                        "90%",
                    ),
                ],
            ),
            dashboard_container::view(
                "LNET Usage",
                div![
                    class![C.h_80, C.p_2],
                    grafana_chart::view(
                        IML_METRICS_DASHBOARD_ID,
                        IML_METRICS_DASHBOARD_NAME,
                        create_chart_params(36, vec![("host_name", &model.host_name)]),
                        "90%",
                    ),
                ],
            ),
        ]
    ]
}
