use crate::{
    components::{
        chart::fs_usage,
        dashboard::{dashboard_container, dashboard_fs_usage},
        datepicker::datepicker,
        grafana_chart::{self, create_chart_params, IML_METRICS_DASHBOARD_ID, IML_METRICS_DASHBOARD_NAME},
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

#[derive(Clone, Debug)]
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
        class![C.grid, C.lg__grid_cols_2, C.gap_6],
        vec![
            dashboard_fs_usage::view(&model.fs_usage),
            dashboard_container::view(
                "Filesystem Usage",
                div![
                    class![C.h_80, C.p_2],
                    grafana_chart::view(
                        IML_METRICS_DASHBOARD_ID,
                        IML_METRICS_DASHBOARD_NAME,
                        create_chart_params(31, vec![("fs_name", &model.fs_name)]),
                        "90%",
                    ),
                    datepicker(),
                ],
            ),
            dashboard_container::view(
                "OST Balance",
                div![
                    class![C.h_80, C.p_2],
                    grafana_chart::view(
                        IML_METRICS_DASHBOARD_ID,
                        IML_METRICS_DASHBOARD_NAME,
                        create_chart_params(35, vec![("fs_name", &model.fs_name)]),
                        "90%",
                    ),
                ],
            ),
            dashboard_container::view(
                "MDT Usage",
                div![
                    class![C.h_80, C.p_2],
                    grafana_chart::view(
                        IML_METRICS_DASHBOARD_ID,
                        IML_METRICS_DASHBOARD_NAME,
                        create_chart_params(32, vec![("fs_name", &model.fs_name)]),
                        "90%",
                    ),
                    datepicker(),
                ],
            ),
        ]
    ]
}

pub fn init(orders: &mut impl Orders<Msg, GMsg>) {
    orders.proxy(Msg::FsUsage).send_msg(fs_usage::Msg::FetchData);
}
