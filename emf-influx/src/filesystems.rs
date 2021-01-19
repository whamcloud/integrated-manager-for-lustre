// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::filesystem;
use std::collections::HashMap;

pub type Response = HashMap<String, filesystem::Response>;
pub type InfluxResponse = crate::InfluxResponse<ResponseTuple>;
type ResponseTuple = (
    String,
    Option<u64>,
    Option<u64>,
    Option<u64>,
    Option<u64>,
    Option<u64>,
    Option<u64>,
);

impl From<InfluxResponse> for Response {
    fn from(response: InfluxResponse) -> Self {
        response
            .results
            .into_iter()
            .take(1)
            .filter_map(|result| result.series)
            .flatten()
            .filter_map(|s| {
                let mfs = s.tags.and_then(|h| h.get("fs").map(|fs| fs.to_string()));

                s.values
                    .into_iter()
                    .next()
                    .and_then(|(_, bt, bf, ba, ft, ff, cc)| {
                        mfs.map(|fs| {
                            (
                                fs,
                                filesystem::Response {
                                    bytes_total: bt,
                                    bytes_free: bf,
                                    bytes_avail: ba,
                                    files_total: ft,
                                    files_free: ff,
                                    clients: cc,
                                },
                            )
                        })
                    })
            })
            .collect()
    }
}

pub fn query() -> String {
    String::from(
        r#"SELECT SUM(b_total), SUM(b_free), SUM(b_avail), SUM(f_total), SUM(f_free), SUM(clients)
           FROM (SELECT *
           FROM (
            SELECT LAST(bytes_total) AS b_total
                 , LAST(bytes_free) AS b_free
                 , LAST(bytes_avail) AS b_avail
                 , LAST(files_total) AS f_total
                 , LAST(files_free) AS f_free
            FROM target
            WHERE "kind" = 'OST'
            GROUP BY target),
            (SELECT LAST(connected_clients) AS clients
            FROM target
            WHERE "kind"='MDT'
            GROUP BY fs))
           GROUP BY fs"#,
    )
    .split_whitespace()
    .collect::<Vec<&str>>()
    .join(" ")
}
