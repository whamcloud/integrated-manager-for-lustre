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
pub static FS_USAGE_QUERY: &str = "SELECT last(bytes_used) AS bytes_used, last(bytes_avail) AS bytes_avail, \
last(bytes_total) AS bytes_total FROM(SELECT SUM(bytes_used) AS bytes_used FROM (SELECT (LAST(\"bytes_total\") \
- LAST(\"bytes_free\")) AS bytes_used FROM \"target\" WHERE \"kind\" = '\"OST\"' GROUP BY target)),\
(SELECT SUM(bytes_avail) AS bytes_avail FROM(SELECT LAST(\"bytes_avail\") AS bytes_avail from \"target\" \
WHERE \"kind\" = '\"OST\"' GROUP BY target)), (SELECT SUM(bytes_total) AS bytes_total FROM(SELECT \
LAST(\"bytes_total\") AS bytes_total from \"target\" WHERE \"kind\" = '\"OST\"' GROUP BY target))";

pub enum ChartColor {
    Red,
    Yellow,
    Green,
    Gray,
}

fn match_range(val: f64, min: f64, max: f64) -> bool {
    val >= min && val <= max
}

impl From<f64> for ChartColor {
    fn from(f: f64) -> ChartColor {
        match f {
            _ if match_range(f, 0.75, 1.0) => ChartColor::Red,
            _ if match_range(f, 0.50, 0.75) => ChartColor::Yellow,
            _ if match_range(f, 0.0, 0.50) => ChartColor::Green,
            _ => ChartColor::Gray,
        }
    }
}

impl Default for ChartColor {
    fn default() -> Self {
        ChartColor::Gray
    }
}

impl<'a> From<&ChartColor> for &str {
    fn from(f: &ChartColor) -> Self {
        match f {
            ChartColor::Green => C.text_green_400,
            ChartColor::Yellow => C.text_yellow_500,
            ChartColor::Red => C.text_red_500,
            ChartColor::Gray => C.text_gray_500,
        }
    }
}

#[derive(Default)]
pub struct Model {
    pub metric_data: Option<FsUsage>,
    pub usage_color: ChartColor,
    circumference: f64,
    pub percent_used: f64,
    stroke_length: f64,
    cancel: Option<oneshot::Sender<()>>,
}

#[derive(serde::Deserialize, Clone, Debug)]
pub struct InfluxSeries {
    #[serde(skip)]
    name: String,
    #[serde(skip)]
    columns: Vec<String>,
    values: Vec<(String, f64, f64, f64)>,
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
    pub bytes_used: f64,
    pub bytes_avail: f64,
    pub bytes_total: f64,
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
        Msg::DataFetched(influx_data) => {
            match influx_data {
                Ok(influx_data) => {
                    let result: &InfluxResult = &influx_data.results[0];

                    if let Some(series) = &(*result).series {
                        let bytes_used = series[0].values[0].1;
                        let bytes_avail = series[0].values[0].2;
                        let bytes_total = series[0].values[0].3;
                        model.metric_data = Some(FsUsage {
                            bytes_used,
                            bytes_avail,
                            bytes_total,
                        });

                        model.circumference = calc_circumference(90.0);
                        model.percent_used = bytes_used / bytes_total;
                        model.stroke_length = calc_percentage(model.circumference, model.percent_used);
                        let usage_color: ChartColor = model.percent_used.into();
                        model.usage_color = usage_color;
                    }
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

fn calc_circumference(radius: f64) -> f64 {
    2.0 * std::f64::consts::PI * radius
}

fn calc_percentage(circumference: f64, val: f64) -> f64 {
    (1.0 - val) * circumference
}

pub fn view<T>(model: &Model) -> Node<T> {
    match &model.metric_data {
        Some(_) => div![
            class![C.stroke_current, C.fill_current],
            svg![
                class![C.transform, C._rotate_90],
                attrs! {
                  At::ViewBox => "0 0 200 200"
                },
                circle![
                    class![
                        C.stroke_5,
                        C.text_gray_200,
                        C.transition_stroke_dashoffset,
                        C.duration_500,
                        C.ease_linear
                    ],
                    attrs! {
                      At::R => "90",
                      At::Cx => "100",
                      At::Cy => "100",
                      At::Fill => "transparent",
                    }
                ],
                circle![
                    class![
                        C.stroke_5,
                        (&model.usage_color).into(),
                        C.transition_stroke_dashoffset,
                        C.duration_500,
                        C.ease_linear
                    ],
                    attrs! {
                      At::R => "90",
                      At::Cx => "100",
                      At::Cy => "100",
                      At::Fill => "transparent",
                      At::StrokeDashArray => model.circumference,
                      At::StrokeDashOffset => model.stroke_length
                    }
                ],
                text![
                    class![
                        C.rotate_90
                        C.origin_center,
                        C.stroke_2,
                        C.text_4xl,
                        C.transform,
                        (&model.usage_color).into(),
                    ],
                    attrs! {
                      At::X => "50%",
                      At::Y => "50%",
                      At::DominantBaseline => "central",
                      At::TextAnchor => "middle"
                    },
                    tspan![format!("{}", (100.0 * model.percent_used) as u16)],
                    tspan![class![C.text_gray_400], "%"]
                ]
            ]
        ],
        None => div!["Loading"],
    }
}
