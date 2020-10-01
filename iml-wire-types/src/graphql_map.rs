// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use std::collections::HashMap;

#[derive(serde::Deserialize, serde::Serialize, Debug)]
pub struct GraphQLMap(pub HashMap<String, serde_json::Value>);

#[cfg(feature = "graphql")]
#[juniper::graphql_scalar(
    name = "Map",
    description = "A Map type"
)]
impl<S> GraphQLScalar for GraphQLMap
where
    S: juniper::ScalarValue,
{
    fn resolve(&self) -> juniper::Value {
        juniper::Value::scalar(serde_json::to_string(&self.0).expect("convert map to string"))
    }

    fn from_input_value(value: &juniper::InputValue) -> Option<GraphQLMap> {
        let v = value.as_string_value()?;
        serde_json::from_str(v).map(|x| GraphQLMap(x)).ok()
    }

    fn from_str<'a>(value: juniper::ScalarToken<'a>) -> juniper::ParseScalarResult<'a, S> {
        <String as juniper::ParseScalarValue<S>>::from_str(value)
    }
}
