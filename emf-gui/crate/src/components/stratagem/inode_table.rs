// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{components::table as t, generated::css_classes::C, sleep_with_handle, GMsg};
use chrono::offset::{TimeZone, Utc};
use futures::channel::oneshot;
use number_formatter::format_bytes;
use seed::{prelude::*, *};
use std::time::Duration;

#[derive(serde::Deserialize, serde::Serialize, Debug, Eq, PartialEq, Ord, PartialOrd, Clone)]
pub(crate) struct INodeCount {
    count: u64,
    size: i64,
    uid: String,
    timestamp: i64,
}

pub struct Model {
    pub(crate) fs_name: String,
    pub(crate) last_known_scan: Option<String>,
    inodes: Vec<INodeCount>,
    cancel: Option<oneshot::Sender<()>>,
}

impl Model {
    pub fn new(fs_name: &str) -> Self {
        Self {
            fs_name: fs_name.to_string(),
            inodes: Default::default(),
            cancel: Default::default(),
            last_known_scan: Default::default(),
        }
    }
}

#[derive(Clone, Debug)]
pub enum Msg {
    FetchInodes,
    InodesFetched(Box<fetch::ResponseDataResult<InfluxResults>>),
    Noop,
}

#[derive(serde::Deserialize, Clone, Debug)]
pub struct InfluxSeries {
    #[serde(skip)]
    name: String,
    #[serde(skip)]
    columns: Vec<String>,
    values: Vec<(i64, String, u64, i64)>,
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

pub(crate) fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::FetchInodes => {
            model.cancel = None;
            let url:String = format!("/influx?db=emf_stratagem_scans&epoch=ns&q=SELECT%20counter_name,%20count,%20size%20FROM%20stratagem_scan%20WHERE%20group_name=%27user_distribution%27%20and%20fs_name=%27{}%27%20limit%2020", &model.fs_name);
            let request = seed::fetch::Request::new(url);

            orders
                .skip()
                .perform_cmd(request.fetch_json_data(|x| Msg::InodesFetched(Box::new(x))));
        }
        Msg::InodesFetched(fetch_object) => {
            match *fetch_object {
                Ok(response) => {
                    model.inodes = response
                        .results
                        .into_iter()
                        .take(1)
                        .filter_map(|result| result.series)
                        .flatten()
                        .take(1)
                        .map(|v| v.values)
                        .flatten()
                        .map(|(timestamp, uid, count, size)| INodeCount {
                            timestamp,
                            uid,
                            count,
                            size,
                        })
                        .collect();

                    model.inodes.sort_by(|a, b| b.cmp(a));

                    model.last_known_scan = model.inodes.first().map(|x| get_date_time(x.timestamp));
                }
                Err(fail_reason) => {
                    error!(fail_reason);
                    orders.skip();
                }
            }

            let (cancel, fut) = sleep_with_handle(Duration::from_secs(60), Msg::FetchInodes, Msg::Noop);
            model.cancel = Some(cancel);
            orders.perform_cmd(fut);
        }
        Msg::Noop => {
            orders.skip();
        }
    }
}

fn get_date_time(timestamp: i64) -> String {
    let dt = Utc.timestamp_nanos(timestamp);

    dt.format("%A, %B %d, %Y %H:%M:%S %Z").to_string()
}

pub(crate) fn view(model: &Model) -> Node<Msg> {
    div![
        class![
            C.bg_white,
            C.border,
            C.border_b,
            C.border_t,
            C.mt_24,
            C.rounded_lg,
            C.shadow,
        ],
        div![
            class![C.flex, C.justify_between, C.px_6, C._mb_px, C.bg_gray_200],
            h3![class![C.py_4, C.font_normal, C.text_lg], "Top inode Users"],
            p![
                class![C.py_4, C.text_gray_600],
                "Last Scanned: ",
                model.last_known_scan.as_ref().unwrap_or(&"---".to_string())
            ]
        ],
        table![
            class![C.table_fixed, C.w_full],
            style! {
                St::BorderSpacing => px(10),
                St::BorderCollapse => "initial"
            },
            vec![
                t::thead_view(vec![
                    t::th_view(plain!["Name"]),
                    t::th_view(plain!["Count"]),
                    t::th_view(plain!["Space Used"])
                ]),
                tbody![model.inodes.iter().map(|i| tr![
                    t::td_view(plain![i.uid.clone()]),
                    t::td_center(plain![i.count.to_string()]),
                    t::td_center(plain![format_bytes(i.size as f64, None)])
                ])]
            ]
        ]
    ]
}
