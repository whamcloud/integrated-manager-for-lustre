// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use seed::{iframe, attrs, prelude::*};

/// Create an iframe that loads the specified stratagem chart
pub fn grafana_chart<T>(dashboard_id: &str, dashboard_name: &str, refresh: &str, panel_id: u16, width: &str, height: &str) -> El<T> {
    iframe![
        attrs! { 
            At::Src => format!("https://localhost:8443/grafana/d-solo/{}/{}?orgId=1&refresh={}&panelId={}", dashboard_id, dashboard_name, refresh, panel_id),
            At::Width => width,
            At::Height => height,
            "frameborder" => 0
         }
    ]
}
