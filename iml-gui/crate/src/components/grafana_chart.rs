// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use seed::{attrs, iframe, prelude::*};
use serde_with::with_prefix;
use std::collections::HashMap;

use seed::{attrs, iframe, p, prelude::*};

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
    pub vars: &'a HashMap<String, String>,
}

pub(crate) fn create_chart_params(panel_id: u32, vars: impl Into<Option<HashMap<String, String>>>) {
    GrafanaChartData {
        org_id: 1,
        refresh: "10s",
        panel_id,
        vars: vars.into(),
    }
}

/// Create an iframe that loads the specified stratagem chart
pub(crate) fn view<T>(dashboard_id: &str, dashboard_name: &str, chart_data: impl serde::Serialize) -> Node<T> {
    iframe![attrs! {
        At::Src => format!("grafana/d-solo/{}/{}?{}", dashboard_id, dashboard_name, serde_urlencoded::to_string(chart_data).unwrap()),
        "frameborder" => 0
    }]
}
