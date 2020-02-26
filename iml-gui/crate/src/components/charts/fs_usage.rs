// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    GMsg,
    {generated::css_classes::C, sleep::sleep_with_handle},
};
use futures::channel::oneshot;
use seed::{prelude::*, Request, *};
use number_formatter;
use std::time::Duration;

pub static DB_NAME: &str = "iml_stats";
pub static FS_USAGE_QUERY: &str = "SELECT last(bytes_used) AS bytes_used, last(bytes_avail) AS bytes_avail \
FROM(SELECT SUM(bytes_used) AS bytes_used FROM (SELECT (LAST(\"bytes_total\") - LAST(\"bytes_free\")) AS bytes_used \
FROM \"target\" WHERE \"kind\" = '\"OST\"' GROUP BY target)),(SELECT SUM(bytes_avail) AS bytes_avail FROM(SELECT LAST(\"bytes_avail\") \
AS bytes_avail from \"target\" WHERE \"kind\" = '\"OST\"' GROUP BY target))";

enum ChartColor {
  Red,
  Yellow,
  Green,
}

fn match_range(val: f64, min: f64, max: f64) -> bool {
  val >= min && val <= max
}

impl From<f64> for ChartColor {
  fn from(f: f64) -> ChartColor {
    match f {
      _ if match_range(f, 0.50, 1.0) => ChartColor::Green,
      _ if match_range(f, 0.25, 0.50) => ChartColor::Yellow,
      _ if match_range(f, 0.0, 0.25) => ChartColor::Red,
      _ => ChartColor::Red
    }
  }
}

impl<'a> From<ChartColor> for &str {
  fn from(f: ChartColor) -> Self {
    match f {
      ChartColor::Green => C.text_green_500,
      ChartColor::Yellow => C.text_yellow_500,
      ChartColor::Red => C.text_red_500,
    }
  }
}

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
    values: Vec<(String, f64, f64)>,
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
    bytes_used: f64,
    bytes_avail: f64,
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
                  log!(format!("Metric Data: {:#?}", influx_data));
                  let result: &InfluxResult = &influx_data.results[0];

                  if let Some(series) =  &(*result).series {
                    let bytes_used = series[0].values[0].1;
                    let bytes_avail = series[0].values[0].2;
                    model.metric_data = Some(FsUsage {
                      bytes_used,
                      bytes_avail,
                    });
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
  val * circumference
}

pub fn view<T>(model: &Model) -> Node<T> {
    div![
        class![C.bg_white, C.rounded_lg],
        div![
            class![C.px_6, C.bg_gray_200],
            h3![class![C.py_4, C.font_normal, C.text_lg], "Filesystem"]
        ],
        match &model.metric_data {
            Some(x) => {
                let c = calc_circumference(90.0);
                let percent_available = 1.0 - x.bytes_used / x.bytes_avail;
                let p = calc_percentage(c, percent_available);
                let usage_color:ChartColor = percent_available.into();
                let usage_color: &str = usage_color.into();

                div![
                  class![C.flex, C.content_start, C.stroke_current, C.fill_current, C.items_center, C.justify_center, C.h_64],
                  div![
                    class![C.w_1of3, C.text_right, C.p_2],
                    p![
                      class![usage_color],
                      format!("{}", number_formatter::format_bytes(x.bytes_used, Some(1)))
                    ],
                    p![
                        class![C.text_gray_500, C.text_xs],
                        "(Used)"
                      ]
                  ],
                  svg![
                    class![C.w_1of3, C.p_2],
                    attrs!{
                      At::ViewBox => "0 0 195 195"
                    },
                    circle![
                      class![C.stroke_6, usage_color, C.transition_stroke_dashoffset, C.duration_500, C.ease_linear],
                      attrs!{
                        At::R => "90",
                        At::Cx => "100", 
                        At::Cy => "100", 
                        At::Fill => "transparent",
                      }
                    ],
                    circle![
                      class![C.stroke_6, C.text_gray_200, C.transition_stroke_dashoffset, C.duration_500, C.ease_linear],
                      attrs!{
                        At::R => "90",
                        At::Cx => "100", 
                        At::Cy => "100", 
                        At::Fill => "transparent", 
                        At::StrokeDashArray => c, 
                        At::StrokeDashOffset => p
                      }
                    ],
                    text![
                      class![C.stroke_2, usage_color, C.text_4xl],
                      attrs!{
                        At::X => "50%",
                        At::Y => "50%",
                        At::DominantBaseline => "central",
                        At::TextAnchor => "middle"
                      },
                      tspan![format!("{}", (100.0 * percent_available) as u16)],
                      tspan![
                        class!["text-gray-500"], 
                        "%"
                      ]
                    ]
                  ],
                  div![
                    class![C.w_1of3, C.p_2],
                    p![format!("{}", number_formatter::format_bytes(x.bytes_avail, Some(1)))],
                    p![
                      class![C.text_gray_500, C.text_xs],
                      "(Available)"
                    ]
                  ],
                ]
            }
            None => div!["Loading"],
        }
    ]
}
