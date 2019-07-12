// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_environment::grafana_root;
use seed::{attrs, iframe, prelude::*};

/// Create an iframe that loads the specified stratagem chart
pub fn grafana_chart<T>(
    dashboard_id: &str,
    dashboard_name: &str,
    refresh: &str,
    panel_id: u16,
    width: &str,
    height: &str,
) -> El<T> {
    iframe![attrs! {
       At::Src => format!("{}d-solo/{}/{}?orgId=1&refresh={}&panelId={}", grafana_root(), dashboard_id, dashboard_name, refresh, panel_id),
       At::Width => width,
       At::Height => height,
       "frameborder" => 0
    }]
}
