// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub mod logs {
    use crate::{Query, SortDir};
    use iml_wire_types::{LogSeverity, MessageClass, db::LogMessageRecord};

    pub static QUERY: &str = r#"
            query logs(limit: Int, offset: Int, dir: SortDir, message: String, fqdn: String, tag: String, startDatetime: String, endDatetime: String, messageClass: [MessageClass!], severity: LogSeverity) {
                logs(limit: $limit, offset: $offset, dir: $dir, message: $message, fqdn: $fqdn, tag: $tag, startDatetime: $startDatetime, endDatetime: $endDatetime, messageClass: $messageClass, severity: $severity) {
                    id
                    datetime
                    facility
                    fqdn
                    message
                    messageClass
                    severity
                    tag
                }
            }
        "#;

    #[derive(Debug, serde::Serialize)]
    pub struct Vars {
        limit: Option<i32>,
        offset: Option<i32>,
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
        limit: Option<i32>,
        offset: Option<i32>,
        dir: Option<SortDir>,
        message: Option<impl ToString>,
        fqdn: Option<impl ToString>,
        tag: Option<impl ToString>,
        start_datetime: Option<impl ToString>,
        end_datetime: Option<impl ToString>,
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
    pub struct Resp {
        #[serde(rename(deserialize = "logs"))]
        pub logs: Vec<LogMessageRecord>,
    }
}
