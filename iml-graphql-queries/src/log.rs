// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub mod logs {
    use crate::{Query, SortDir};
    use chrono::Utc;
    use iml_wire_types::{LogSeverity, MessageClass};

    pub static QUERY: &str = r#"
            query logs($limit: Int, $offset: Int, $dir: SortDir, $message: String, $fqdn: String, $tag: String, $startDatetime: String, $endDatetime: String, $messageClass: [MessageClass!], $severity: LogSeverity) {
                logs(limit: $limit, offset: $offset, dir: $dir, message: $message, fqdn: $fqdn, tag: $tag, startDatetime: $startDatetime, endDatetime: $endDatetime, messageClass: $messageClass, severity: $severity) {
                    id
                    facility
                    fqdn
                    message
                    tag
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
                message: message.map(|x| x.to_string()),
                fqdn: fqdn.map(|x| x.to_string()),
                tag: tag.map(|x| x.to_string()),
                start_datetime: start_datetime.map(|x| x.to_string()),
                end_datetime: end_datetime.map(|x| x.to_string()),
                message_class,
                severity,
            }),
        }
    }

    #[derive(Debug, Clone, serde::Deserialize)]
    pub struct LogMessage {
        pub id: i32,
        // pub datetime: chrono::DateTime<Utc>,
        pub facility: i32,
        pub fqdn: String,
        pub message: String,
        // pub message_class: MessageClass,
        // pub severity: LogSeverity,
        pub tag: String,
    }

    #[derive(Debug, Clone, serde::Deserialize)]
    pub struct Resp {
        pub logs: Vec<LogMessage>,
    }
}
