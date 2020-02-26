// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use seed::{attrs, iframe, p, prelude::*};

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
pub fn view<T>(
    dashboard_id: &str,
    dashboard_name: &str,
    chart_data: Vec<impl serde::Serialize>,
    height: &str,
) -> Vec<Node<T>> {
    let charts: Vec<Node<T>> = chart_data
        .iter()
        .filter_map(|data| {
            serde_urlencoded::to_string(data).ok().map(|params| {
                iframe![attrs! {
                    At::Src => format!("/grafana/d-solo/{}/{}?{}&kiosk", dashboard_id, dashboard_name, params),
                    At::Width => "100%",
                    At::Height => height,
                    "frameborder" => 0
                }]
            })
        })
        .collect();

    if !charts.is_empty() {
        charts
    } else {
        vec![p!["Couldn't parse chart data."]]
    }
}
