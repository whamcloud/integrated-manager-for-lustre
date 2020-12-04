use crate::graphql::json::convert_to_juniper_value;
use std::collections::HashMap;

#[derive(serde::Deserialize, serde::Serialize, Debug, Clone)]
pub struct GraphQLMap(pub HashMap<String, serde_json::Value>);

#[juniper::graphql_scalar(name = "GraphQLMap", description = "GraphQL Map type")]
impl<S> GraphQLScalar for GraphQLMap
where
    S: juniper::ScalarValue,
{
    fn resolve(&self) -> juniper::Value {
        let mut obj = juniper::Object::with_capacity(self.0.len());
        for (k, v) in &self.0 {
            obj.add_field(k.clone(), convert_to_juniper_value(v));
        }
        juniper::Value::Object(obj)
    }

    fn from_input_value(value: &juniper::InputValue) -> Option<GraphQLMap> {
        let v = value.as_string_value()?;
        serde_json::from_str(v).map(GraphQLMap).ok()
    }

    fn from_str(value: juniper::ScalarToken) -> juniper::ParseScalarResult<S> {
        <String as juniper::ParseScalarValue<S>>::from_str(value)
    }
}
