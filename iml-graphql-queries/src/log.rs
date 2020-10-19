// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub mod logs {
    use crate::Query;
    use iml_wire_types::{LogSeverity, MessageClass, SortDir};

    pub static QUERY: &str = r#"
            query logs($limit: Int, $offset: Int, $dir: SortDir, $message: String, $fqdn: String, $tag: String, $startDatetime: String, $endDatetime: String, $messageClass: [MessageClass!], $severity: LogSeverity) {
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

        pub fn build(self) -> Query<Vars> {
            Query {
                query: QUERY.to_string(),
                variables: Some(self.vars),
            }
        }
    }

    pub fn build(
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
    ) -> Query<Vars> {
        Query {
            query: QUERY.to_string(),
            variables: Some(Vars {
                limit,
                offset,
                dir,
                message,
                fqdn,
                tag,
                start_datetime,
                end_datetime,
                message_class,
                severity,
            }),
        }
    }
}
