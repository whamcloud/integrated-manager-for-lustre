// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub mod list_reports {
    use crate::Query;
    use iml_wire_types::StratagemReport;

    pub static QUERY: &str = r#"
        query StratagemReports {
          stratagemReports {
            filename
            size
            modify_time: modifyTime
          }
        }
    "#;

    #[derive(Debug, serde::Serialize)]
    pub struct Vars {}

    pub fn build() -> Query<Vars> {
        Query {
            query: QUERY.to_string(),
            variables: None,
        }
    }

    #[derive(Debug, Clone, serde::Deserialize)]
    pub struct Resp {
        #[serde(rename(deserialize = "stratagemReports"))]
        pub stratagem_reports: Vec<StratagemReport>,
    }
}

pub mod delete_report {
    use crate::Query;

    pub static QUERY: &str = r#"
        mutation DeleteStratagemReport($filename: String!) {
          deleteStratagemReport(filename: $filename)
        }
    "#;

    #[derive(Debug, serde::Serialize)]
    pub struct Vars {
        filename: String,
    }

    pub fn build(filename: impl ToString) -> Query<Vars> {
        Query {
            query: QUERY.to_string(),
            variables: Some(Vars {
                filename: filename.to_string(),
            }),
        }
    }

    #[derive(Debug, Clone, serde::Deserialize)]
    pub struct Resp {
        #[serde(rename(deserialize = "deleteStratagemReport"))]
        pub delete_stratagem_report: bool,
    }
}
