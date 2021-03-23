// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

#[derive(Debug, Clone, serde::Deserialize)]
pub struct Resp<T> {
    pub alert: T,
}

pub mod list {
    use crate::Query;
    use emf_wire_types::{alert::AlertResponse, AlertRecordType, AlertSeverity, SortDir};

    pub static QUERY: &str = r#"
        query ListAlerts($limit: Int, $offset: Int, $dir: SortDir, $message: String, $active: Boolean, $startDatetime: DateTimeUtc, $endDatetime: DateTimeUtc, $recordType: [AlertRecordType!], $severity: AlertSeverity) {
          alert {
            list(limit: $limit, offset: $offset, dir: $dir, message: $message, active: $active, startDatetime: $startDatetime, endDatetime: $endDatetime, recordType: $recordType, severity: $severity) {
              data {
                id
                alert_item_type_id: alertItemTypeId
                alert_item_id: alertItemId
                alert_type: alertType
                begin
                end
                active
                dismissed
                severity
                record_type: recordType
                variant
                lustre_pid: lustrePid
                message
              }
              meta {
                total_count: totalCount
              }
            }
          }
        }
    "#;

    #[derive(Debug, serde::Serialize)]
    pub struct Vars {
        limit: Option<usize>,
        offset: Option<usize>,
        dir: Option<SortDir>,
        message: Option<String>,
        active: Option<bool>,
        start_datetime: Option<String>,
        end_datetime: Option<String>,
        record_type: Option<Vec<AlertRecordType>>,
        severity: Option<AlertSeverity>,
    }

    #[derive(Debug)]
    pub struct Builder {
        vars: Vars,
    }

    impl Default for Builder {
        fn default() -> Self {
            Self::new()
        }
    }

    impl Builder {
        pub fn new() -> Self {
            Self {
                vars: Vars {
                    limit: None,
                    offset: None,
                    dir: None,
                    message: None,
                    active: None,
                    start_datetime: None,
                    end_datetime: None,
                    record_type: None,
                    severity: None,
                },
            }
        }

        pub fn with_limit(mut self, limit: usize) -> Self {
            self.vars.limit = Some(limit);
            self
        }

        pub fn with_offset(mut self, offset: usize) -> Self {
            self.vars.offset = Some(offset);
            self
        }

        pub fn with_dir(mut self, dir: SortDir) -> Self {
            self.vars.dir = Some(dir);
            self
        }

        pub fn with_message(mut self, message: impl ToString) -> Self {
            self.vars.message = Some(message.to_string());
            self
        }

        pub fn with_active(mut self, active: bool) -> Self {
            self.vars.active = Some(active);
            self
        }

        pub fn with_start_datetime(mut self, start_datetime: impl ToString) -> Self {
            self.vars.start_datetime = Some(start_datetime.to_string());
            self
        }

        pub fn with_end_datetime(mut self, end_datetime: impl ToString) -> Self {
            self.vars.end_datetime = Some(end_datetime.to_string());
            self
        }

        pub fn with_record_type(mut self, record_type: &[AlertRecordType]) -> Self {
            self.vars.record_type = Some(record_type.to_vec());
            self
        }

        pub fn with_severity(mut self, severity: &AlertSeverity) -> Self {
            self.vars.severity = Some(*severity);
            self
        }

        pub fn build(self) -> Query<Vars> {
            Query {
                query: QUERY.to_string(),
                variables: Some(self.vars),
            }
        }
    }

    #[derive(serde::Serialize, serde::Deserialize, Clone, Debug)]
    pub struct AlertList {
        pub list: AlertResponse,
    }

    pub type Resp = super::Resp<AlertList>;
}
