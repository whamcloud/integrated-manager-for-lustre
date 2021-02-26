// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

#[derive(Debug, Eq, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
#[cfg_attr(feature = "graphql", derive(juniper::GraphQLObject))]
pub struct Command {
    pub id: i32,
}
