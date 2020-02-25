// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::components::grafana_chart;
use seed::{class, div, error, h3, iframe, log, p, prelude::*, Request};

pub static DB_NAME: &str = "iml_metrics";
pub static FS_USAGE_QUERY: &str = "SELECT last(bytes_used) AS bytes_used, last(bytes_avail) AS bytes_avail \
FROM(SELECT SUM(bytes_used) AS bytes_used FROM (SELECT (LAST(\"bytes_total\") - LAST(\"bytes_free\")) AS bytes_used \
FROM \"target\" WHERE \"kind\" = '\"OST\"' GROUP BY target)),(SELECT SUM(bytes_avail) AS bytes_avail FROM(SELECT LAST(\"bytes_avail\") \
AS bytes_avail from \"target\" WHERE \"kind\" = '\"OST\"' GROUP BY target))";

pub struct Model {
    metric_data: FsUsage,
}

#[derive(serde::Deserialize, Debug)]
pub struct FsUsage {
    bytes_used: u16,
    bytes_avail: u16,
}

pub enum Msg {
    DataFetched(seed::fetch::ResponseDataResult<FsUsage>),
}

async fn fetch_metrics(db: &str, query: &str) -> Result<Msg, Msg> {
    let url = format!("/influx/?db={}&query={}", db, query);

    Request::new(url).fetch_json_data(Msg::DataFetched).await
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg>) {
    match msg {
        Msg::DataFetched(Ok(metric_data)) => {
            log!(format!("Metric Data: {:#?}", metric_data));
            model.metric_data = metric_data;
        }

        Msg::DataFetched(Err(e)) => {
            error!("Failed to fetch filesystem usage metrics - {:#?}", e);
            orders.skip();
        }
    }
}

pub fn fs_usage_chart<T>(
    dashboard_id: &str,
    dashboard_name: &str,
    title: &str,
    chart_data: impl serde::Serialize,
) -> Node<T> {
    grafana_chart::view(dashboard_id, dashboard_name, title, chart_data)
}
