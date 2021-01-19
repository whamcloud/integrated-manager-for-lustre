// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

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

#[derive(Default, serde::Deserialize, Clone, Debug)]
pub struct Response {
    pub bytes_total: Option<u64>,
    pub bytes_free: Option<u64>,
    pub bytes_avail: Option<u64>,
    pub files_total: Option<u64>,
    pub files_free: Option<u64>,
    pub clients: Option<u64>,
}

impl From<InfluxResponse> for Response {
    fn from(response: InfluxResponse) -> Self {
        response
            .results
            .into_iter()
            .take(1)
            .filter_map(|result| result.series)
            .flatten()
            .take(1)
            .map(|v| v.values)
            .flatten()
            .next()
            .map(|(_, bt, bf, ba, ft, ff, cc)| Self {
                bytes_total: bt,
                bytes_free: bf,
                bytes_avail: ba,
                files_total: ft,
                files_free: ff,
                clients: cc,
            })
            .unwrap_or_default()
    }
}

pub fn query(fs_name: &str) -> String {
    format!(
        r#"SELECT SUM(b_total), SUM(b_free), SUM(b_avail), SUM(f_total), SUM(f_free), SUM(clients)
           FROM (SELECT *
           FROM (SELECT LAST(bytes_total) AS b_total
                      , LAST(bytes_free) AS b_free
                      , LAST(bytes_avail) AS b_avail
                      , LAST(files_total) AS f_total
                      , LAST(files_free) AS f_free
                  FROM target
                  WHERE "kind" = 'OST' AND "fs" = '{fs_name}'
                  GROUP BY target)
               , (SELECT LAST(connected_clients) AS clients
                  FROM target
                  WHERE "fs"='{fs_name}' AND "kind"='MDT'
                  GROUP BY fs))"#,
        fs_name = fs_name
    )
    .split_whitespace()
    .collect::<Vec<&str>>()
    .join(" ")
}
