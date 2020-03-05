// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use seed::{attrs, iframe, prelude::*};
use serde_with::with_prefix;
use std::collections::HashMap;

pub static IML_METRICS_DASHBOARD_ID: &str = "8Klek6wZz";
pub static IML_METRICS_DASHBOARD_NAME: &str = "iml-metrics";

with_prefix!(grafana_var "var-");

#[derive(serde::Serialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct GrafanaChartData<'a> {
    pub org_id: u16,
    pub refresh: &'a str,
    pub panel_id: u16,
    #[serde(flatten, with = "grafana_var")]
    pub vars: HashMap<String, String>,
}

pub(crate) fn create_chart_params<'a>(
    panel_id: u16,
    vars: impl IntoIterator<Item = (impl ToString, impl ToString)>,
) -> GrafanaChartData<'a> {
    let hm: HashMap<String, String> = vars.into_iter().map(|(x, y)| (x.to_string(), y.to_string())).collect();
    GrafanaChartData {
        org_id: 1,
        refresh: "10s",
        panel_id,
        vars: hm,
    }
}

pub fn no_vars() -> Vec<(String, String)> {
    vec![]
}

/// Create an iframe that loads the specified stratagem chart
pub(crate) fn view<'a, T>(
    dashboard_id: &str,
    dashboard_name: &str,
    chart_data: GrafanaChartData<'a>,
    height: &str,
) -> Node<T> {
    iframe![attrs! {
        At::Src => format!("/grafana/d-solo/{}/{}?{}", dashboard_id, dashboard_name, serde_urlencoded::to_string(chart_data).unwrap()),
        At::Width => "100%",
        At::Height => height,
        "frameborder" => 0
    }]
}
