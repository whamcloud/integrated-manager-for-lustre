// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

#[derive(Debug, Clone, serde::Deserialize)]
pub struct Resp<T> {
    pub state_machine: T,
}

pub mod input_document {
    use crate::Query;

    pub static QUERY: &str = r#"
        mutation SubmitInputDocument($input_doc: String!) {
            stateMachine {
                submitInputDocument(inputDoc: $input_doc) {
                    command
                }
            }
        }
    "#;

    #[derive(Debug, serde::Serialize)]
    pub struct Vars {
        input_doc: String,
    }

    pub fn build(
        input_doc: String,
    ) -> Query<Vars> {
        Query {
            query: QUERY.to_string(),
            variables: Some(Vars {
                input_doc,
            })
        }
    }

    #[derive(Debug, Clone, serde::Deserialize)]
    pub struct SubmitInputDocument {
        #[serde(rename(deserialize = "submitInputDocument"))]
        pub submit_input_document: Command,
    }

    pub type Resp = super::Resp<SubmitInputDocument>;
}
