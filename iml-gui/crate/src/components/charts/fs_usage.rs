// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    GMsg,
    {generated::css_classes::C, sleep::sleep_with_handle},
};
use futures::channel::oneshot;
use seed::{prelude::*, Request, *};
use std::time::Duration;

pub static DB_NAME: &str = "iml_stats";
pub static FS_USAGE_QUERY: &str = "SELECT last(bytes_used) AS bytes_used, last(bytes_avail) AS bytes_avail \
FROM(SELECT SUM(bytes_used) AS bytes_used FROM (SELECT (LAST(\"bytes_total\") - LAST(\"bytes_free\")) AS bytes_used \
FROM \"target\" WHERE \"kind\" = '\"OST\"' GROUP BY target)),(SELECT SUM(bytes_avail) AS bytes_avail FROM(SELECT LAST(\"bytes_avail\") \
AS bytes_avail from \"target\" WHERE \"kind\" = '\"OST\"' GROUP BY target))";

#[derive(Default)]
pub struct Model {
    metric_data: Option<FsUsage>,
    cancel: Option<oneshot::Sender<()>>,
}

#[derive(serde::Deserialize, Clone, Debug)]
pub struct InfluxSeries {
    #[serde(skip)]
    name: String,
    #[serde(skip)]
    columns: Vec<String>,
    values: Vec<(String, u64, u64)>,
}

#[derive(serde::Deserialize, Clone, Debug)]
pub struct InfluxResult {
    #[serde(skip)]
    statement_id: u16,
    series: Option<Vec<InfluxSeries>>,
}

#[derive(serde::Deserialize, Clone, Debug)]
pub struct InfluxResults {
    results: Vec<InfluxResult>,
}

#[derive(serde::Deserialize, Clone, Debug)]
pub struct FsUsage {
    bytes_used: u16,
    bytes_avail: u16,
}

#[derive(Clone)]
pub enum Msg {
    DataFetched(seed::fetch::ResponseDataResult<InfluxResults>),
    FetchData,
    Noop,
}

async fn fetch_metrics(db: &str, query: &str) -> Result<Msg, Msg> {
    let url = format!("/influx?db={}&q={}", db, query);

    Request::new(url).fetch_json_data(Msg::DataFetched).await
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::FetchData => {
            orders.skip().perform_cmd(fetch_metrics(DB_NAME, FS_USAGE_QUERY));
        }
        Msg::DataFetched(metric_data) => {
            match metric_data {
                Ok(metric_data) => {
                    log!(format!("Metric Data: {:#?}", metric_data));
                    // model.metric_data = Some(metric_data);
                }
                Err(e) => {
                    error!("Failed to fetch filesystem usage metrics - {:#?}", e);
                    orders.skip();
                }
            }

            let (cancel, fut) = sleep_with_handle(Duration::from_secs(10), Msg::FetchData, Msg::Noop);

            model.cancel = Some(cancel);

            orders.perform_cmd(fut);
        }
        Msg::Noop => {}
    }
}

pub fn view<T>(model: &Model) -> Node<T> {
    div![
        class![C.bg_white, C.rounded_lg, C.h_64],
        div![
            class![C.px_6, C.bg_gray_200],
            h3![class![C.py_4, C.font_normal, C.text_lg], "Filesystem"]
        ],
        match &model.metric_data {
            Some(x) => {
                log!(x);
                svg![]
            }
            None => div!["Loading"],
        }
    ]
}
