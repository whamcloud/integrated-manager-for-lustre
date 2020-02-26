// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::generated::css_classes::C;
use seed::{attrs, class, div, h3, iframe, p, prelude::*};

pub static IML_METRICS_DASHBOARD_ID: &str = "8Klek6wZz";
pub static IML_METRICS_DASHBOARD_NAME: &str = "iml-metrics";

#[derive(Debug, Default, serde::Serialize)]
#[serde(rename_all = "camelCase")]
pub struct DashboardChart<'a> {
    pub org_id: u16,
    pub refresh: &'a str,
    pub panel_id: u16,
}

#[derive(Debug, Default, serde::Serialize)]
#[serde(rename_all = "camelCase")]
pub struct FsDashboardChart<'a> {
    pub org_id: u16,
    #[serde(rename(serialize = "var-fs_name"))]
    pub var_fs_name: &'a str,
    pub refresh: &'a str,
    pub panel_id: u16,
}

#[derive(Debug, Default, serde::Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ServerDashboardChart<'a> {
    pub org_id: u16,
    #[serde(rename(serialize = "var-host_name"))]
    pub var_host_name: &'a str,
    pub refresh: &'a str,
    pub panel_id: u16,
}

#[derive(Debug, Default, serde::Serialize)]
#[serde(rename_all = "camelCase")]
pub struct TargetDashboardChart<'a> {
    pub org_id: u16,
    #[serde(rename(serialize = "var-target_name"))]
    pub var_target_name: &'a str,
    pub refresh: &'a str,
    pub panel_id: u16,
}

/// Create an iframe that loads the specified stratagem chart
pub fn view<T>(dashboard_id: &str, dashboard_name: &str, title: &str, chart_data: impl serde::Serialize) -> Node<T> {
    let params = serde_urlencoded::to_string(chart_data);
    if let Ok(params) = params {
        div![
            class![C.bg_white, C.rounded_lg, C.h_64],
            div![
                class![C.px_6, C.bg_gray_200],
                h3![class![C.py_4, C.font_normal, C.text_lg], title]
            ],
            iframe![
                class![C.p_2],
                attrs! {
                    At::Src => format!("/grafana/d-solo/{}/{}?{}&kiosk", dashboard_id, dashboard_name, params),
                    At::Width => "100%",
                    At::Height => "77%",
                    "frameborder" => 0
                }
            ]
        ]
    } else {
        p!["Couldn't parse chart data."]
    }
}
