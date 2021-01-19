// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use seed::{attrs, iframe, prelude::*};
use std::collections::BTreeMap;

pub static EMF_METRICS_DASHBOARD_ID: &str = "8Klek6wZz";
pub static EMF_METRICS_DASHBOARD_NAME: &str = "emf-metrics";

#[derive(serde::Serialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct GrafanaChartData<'a> {
    pub org_id: u16,
    pub refresh: &'a str,
    pub panel_id: u16,
    #[serde(flatten)]
    pub vars: BTreeMap<String, String>,
}

pub(crate) fn create_chart_params(
    panel_id: u16,
    refresh: &str,
    vars: impl IntoIterator<Item = (impl ToString, impl ToString)>,
) -> GrafanaChartData {
    let hm: BTreeMap<String, String> = vars
        .into_iter()
        .map(|(x, y)| {
            let var = x.to_string();
            let key = match var.as_str() {
                "to" | "from" => var.to_string(),
                _ => format!("var-{}", var),
            };

            (key, y.to_string())
        })
        .collect();

    GrafanaChartData {
        org_id: 1,
        refresh,
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
        At::Src => format!("/grafana/d-solo/{}/{}?kiosk&{}", dashboard_id, dashboard_name, serde_urlencoded::to_string(chart_data).unwrap()),
        At::Width => "100%",
        At::Height => height,
        "frameborder" => 0
    }]
}
