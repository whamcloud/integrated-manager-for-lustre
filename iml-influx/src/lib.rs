// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub mod filesystem;
pub mod filesystems;

#[cfg(feature = "with-db-client")]
use futures::{future::BoxFuture, FutureExt};
#[cfg(feature = "with-db-client")]
pub use influx_db_client::{Client, Point, Points, Precision, Value};
use serde_json::Map;
use std::collections::HashMap;

#[cfg(feature = "with-db-client")]
#[derive(Debug, thiserror::Error)]
pub enum Error {
    #[error(transparent)]
    InfluxDbError(#[from] influx_db_client::Error),
    #[error(transparent)]
    Serde(#[from] serde_json::Error),
}

#[cfg(feature = "with-db-client")]
pub trait InfluxClientExt {
    fn query_into<T: serde::de::DeserializeOwned>(
        &self,
        q: &str,
        epoch: Option<Precision>,
    ) -> BoxFuture<Result<Option<Vec<T>>, Error>>;
}

#[cfg(feature = "with-db-client")]
impl InfluxClientExt for Client {
    fn query_into<T: serde::de::DeserializeOwned>(
        &self,
        q: &str,
        epoch: Option<Precision>,
    ) -> BoxFuture<Result<Option<Vec<T>>, Error>> {
        let q = self.query(q, epoch);

        async move {
            let r = q.await?;

            let x = if let Some(nodes) = r {
                let items = nodes
                    .into_iter()
                    .filter_map(|x| x.series)
                    .flatten()
                    .map(|x| -> serde_json::Value { ColVals(x.columns, x.values).into() })
                    .map(|x| -> Result<Vec<T>, Error> {
                        let x = serde_json::from_value(x)?;

                        Ok(x)
                    })
                    .collect::<Result<Vec<Vec<T>>, _>>()?;

                Some(Ok(items.into_iter().flatten().collect()))
            } else {
                None
            };

            x.transpose()
        }
        .boxed()
    }
}

#[derive(serde::Deserialize, Clone, Debug)]
pub struct InfluxResponse<T> {
    results: Vec<InfluxResult<T>>,
}

#[derive(serde::Deserialize, Clone, Debug)]
pub struct InfluxResult<T> {
    series: Option<Vec<InfluxSeries<T>>>,
}

#[derive(serde::Deserialize, Clone, Debug)]
pub struct InfluxSeries<T> {
    tags: Option<HashMap<String, String>>,
    values: Vec<T>,
}

pub struct ColVals(pub Vec<String>, pub Vec<Vec<serde_json::Value>>);

impl From<ColVals> for serde_json::Value {
    fn from(ColVals(cols, vals): ColVals) -> Self {
        let xs = vals
            .into_iter()
            .map(|y| -> Map<String, serde_json::Value> {
                cols.clone().into_iter().zip(y).collect()
            })
            .map(serde_json::Value::Object)
            .collect();

        serde_json::Value::Array(xs)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use influx_db_client::keys::{Node, Series};
    use serde_json::json;

    #[test]
    fn test_col_vals_to_value() {
        let query_result = vec![Node {
            statement_id: Some(0),
            series: Some(vec![Series {
                name: "col1".to_string(),
                tags: None,
                columns: vec!["time".into(), "col1".into(), "col2".into(), "col3".into()],
                values: vec![
                    vec![
                        json!(1597166951257510515_i64),
                        json!("foo1"),
                        json!("bar1"),
                        json!("baz1"),
                    ],
                    vec![
                        json!(1597166951257510515_i64),
                        json!("foo2"),
                        json!("bar2"),
                        json!("baz2"),
                    ],
                ],
            }]),
        }];

        #[derive(Debug, serde::Deserialize, PartialEq)]
        struct Record {
            col1: String,
            col2: String,
            col3: String,
        }

        let records = query_result
            .into_iter()
            .filter_map(|x| x.series)
            .flatten()
            .map(|x| -> serde_json::Value { ColVals(x.columns, x.values).into() })
            .map(|x| {
                let x: Vec<Record> =
                    serde_json::from_value(x).expect("Couldn't convert to record.");
                x
            })
            .flatten()
            .collect::<Vec<Record>>();

        assert_eq!(
            records,
            vec![
                Record {
                    col1: "foo1".into(),
                    col2: "bar1".into(),
                    col3: "baz1".into(),
                },
                Record {
                    col1: "foo2".into(),
                    col2: "bar2".into(),
                    col3: "baz2".into(),
                }
            ]
        );
    }
}
