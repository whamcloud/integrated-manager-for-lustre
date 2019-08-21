// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_environment::grafana_root;
use seed::{attrs, iframe, p, prelude::*};

pub static GRAFANA_DASHBOARD_ID: &str = "OBdCS5IWz";
pub static GRAFANA_DASHBOARD_NAME: &str = "stratagem";

#[derive(Debug, Default, serde::Serialize)]
#[serde(rename_all = "camelCase")]
pub struct GrafanaChartData<'a> {
    pub org_id: u16,
    #[serde(rename(serialize = "var-fs_name"))]
    pub var_fs_name: &'a str,
    pub refresh: &'a str,
    pub panel_id: u16,
}

/// Create an iframe that loads the specified stratagem chart
pub fn grafana_chart<T>(
    dashboard_id: &str,
    dashboard_name: &str,
    width: &str,
    height: &str,
    chart_data: impl serde::Serialize,
) -> Node<T> {
    let params = serde_urlencoded::to_string(chart_data);
    if let Ok(params) = params {
        iframe![attrs! {
            At::Src => format!("{}d-solo/{}/{}?{}", grafana_root(), dashboard_id, dashboard_name, params),
            At::Width => width,
            At::Height => height,
            "frameborder" => 0
        }]
    } else {
        p!["Couldn't parse chart data."]
    }
}
