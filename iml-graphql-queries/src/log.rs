// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub mod logs {
    use crate::Query;
    use iml_wire_types::{logs::LogResponse, LogSeverity, MessageClass, SortDir};

    pub static QUERY: &str = r#"
            query logs($limit: Int, $offset: Int, $dir: SortDir, $message: String, $fqdn: String, $tag: String, $startDatetime: DateTimeUtc, $endDatetime: DateTimeUtc, $messageClass: [MessageClass!], $severity: LogSeverity) {
                logs(limit: $limit, offset: $offset, dir: $dir, message: $message, fqdn: $fqdn, tag: $tag, startDatetime: $startDatetime, endDatetime: $endDatetime, messageClass: $messageClass, severity: $severity) {
                    data {
                        id
                        datetime
                        facility
                        fqdn
                        message
                        message_class: messageClass
                        severity
                        tag
                    }
                    meta {
                        total_count: totalCount
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
        fqdn: Option<String>,
        tag: Option<String>,
        start_datetime: Option<String>,
        end_datetime: Option<String>,
        message_class: Option<Vec<MessageClass>>,
        severity: Option<LogSeverity>,
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
                    fqdn: None,
                    tag: None,
                    start_datetime: None,
                    end_datetime: None,
                    message_class: None,
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

        pub fn with_fqdn(mut self, fqdn: impl ToString) -> Self {
            self.vars.fqdn = Some(fqdn.to_string());
            self
        }

        pub fn with_tag(mut self, tag: impl ToString) -> Self {
            self.vars.tag = Some(tag.to_string());
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

        pub fn with_message_class(mut self, message_class: &[MessageClass]) -> Self {
            self.vars.message_class = Some(message_class.to_vec());
            self
        }

        pub fn with_severity(mut self, severity: &LogSeverity) -> Self {
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
    pub struct Resp {
        pub logs: LogResponse,
    }
}
