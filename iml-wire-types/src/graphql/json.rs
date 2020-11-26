#[derive(serde::Deserialize, serde::Serialize, Debug, Clone)]
pub struct GraphQLJson(pub serde_json::Value);

#[juniper::graphql_scalar(
    name = "Json",
    description = "An opaque json value",
)]
impl<S> GraphQLScalar for GraphQLJson
    where
        S: juniper::ScalarValue,
{
    fn resolve(&self) -> juniper::Value {
        convert_to_juniper_value(&self.0)
    }

    fn from_input_value(value: &juniper::InputValue) -> Option<GraphQLJson> {
        value.as_string_value().and_then(|s| {
            serde_json::from_str::<serde_json::Value>(s)
                .ok()
                .map(GraphQLJson)
        })
    }

    fn from_str(value: juniper::ScalarToken) -> juniper::ParseScalarResult<S> {
        <String as juniper::ParseScalarValue<S>>::from_str(value)
    }
}

pub fn convert_to_juniper_value<S>(json: &serde_json::Value) -> juniper::Value<S>
    where
        S: juniper::ScalarValue,
{
    match json {
        serde_json::Value::Null => juniper::Value::null(),
        serde_json::Value::Bool(b) => juniper::Value::scalar(*b),
        serde_json::Value::Number(n) => {
            if let Some(n) = n.as_u64() {
                juniper::Value::scalar(n as i32)
            } else if let Some(n) = n.as_i64() {
                juniper::Value::scalar(n as i32)
            } else if let Some(n) = n.as_f64() {
                juniper::Value::scalar(n)
            } else {
                unreachable!("serde_json::Number has only 3 number variants")
            }
        }
        serde_json::Value::String(s) => juniper::Value::scalar(s.clone()),
        serde_json::Value::Array(a) => {
            let arr = a
                .iter()
                .map(|v| convert_to_juniper_value(v))
                .collect::<Vec<_>>();
            juniper::Value::list(arr)
        }
        serde_json::Value::Object(o) => {
            let obj: juniper::Object<S> = o
                .iter()
                .map(|(k, v)| (k, convert_to_juniper_value(v)))
                .collect();
            juniper::Value::object(obj)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::convert_to_juniper_value;
    use juniper::DefaultScalarValue;

    #[test]
    pub fn test_conv() {
        let j = serde_json::json!({
          "key 1": {},
          "key 2": [],
          "key 3": [{}],
          "key 3": [1, "a", true, null],
          "key 5": {
            "2018-10-26": { "x": "", "y": [ "106.9600" ] },
            "2018-10-25": { "x": 2.1, "y": { "arg": 106.9600 } }
          }
        });

        let o = convert_to_juniper_value::<DefaultScalarValue>(&j);
        let exp = "{\
            \"key 1\": {}, \
            \"key 2\": [], \
            \"key 3\": [1, \"a\", true, null], \
            \"key 5\": {\
                \"2018-10-26\": {\"x\": \"\", \"y\": [\"106.9600\"]}, \
                \"2018-10-25\": {\"x\": 2.1, \"y\": {\"arg\": 106.96}}\
            }\
        }";

        assert_eq!(o.to_string(), exp);
    }
}
