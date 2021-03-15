// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

#[derive(Debug, Clone, serde::Deserialize)]
pub struct Resp<T> {
    #[serde(rename(deserialize = "stateMachine"))]
    pub state_machine: T,
}

pub mod input_document {
    use crate::Query;
    use emf_wire_types::Command;

    pub static QUERY: &str = r#"
        mutation SubmitInputDocument($input_doc: String!) {
          stateMachine {
            submitInputDocument(document: $input_doc) {
              id
              plan
              state
            }
          }
        }"#;

    #[derive(Debug, serde::Serialize)]
    pub struct Vars {
        input_doc: String,
    }

    pub fn build(input_doc: String) -> Query<Vars> {
        Query {
            query: QUERY.to_string(),
            variables: Some(Vars { input_doc }),
        }
    }

    #[derive(Debug, Clone, serde::Deserialize)]
    pub struct SubmitInputDocument {
        #[serde(rename(deserialize = "submitInputDocument"))]
        pub submit_input_document: Command,
    }

    pub type Resp = super::Resp<SubmitInputDocument>;
}

pub mod list_cmds {
    use crate::Query;
    use emf_wire_types::Command;

    pub static QUERY: &str = r#"
        query ListCmds {
          stateMachine {
            listCmds {
              id
              plan
              state
            }
          }
        }"#;

    pub fn build() -> Query<()> {
        Query {
            query: QUERY.to_string(),
            variables: None,
        }
    }

    #[derive(Debug, Clone, serde::Deserialize)]
    pub struct ListCmds {
        #[serde(rename(deserialize = "listCmds"))]
        pub list_cmds: Vec<Command>,
    }

    pub type Resp = super::Resp<ListCmds>;
}

pub mod get_cmd {
    use crate::Query;
    use emf_wire_types::Command;

    pub static QUERY: &str = r#"
        query GetCmd($id: Int!) {
          stateMachine {
            getCmd(id: $id) {
              id
              plan
              state
            }
          }
        }"#;

    #[derive(Debug, serde::Serialize)]
    pub struct Vars {
        id: i32,
    }

    pub fn build(id: i32) -> Query<Vars> {
        Query {
            query: QUERY.to_string(),
            variables: Some(Vars { id }),
        }
    }

    #[derive(Debug, Clone, serde::Deserialize)]
    pub struct GetCmd {
        #[serde(rename(deserialize = "getCmd"))]
        pub get_cmd: Option<Command>,
    }

    pub type Resp = super::Resp<GetCmd>;
}
