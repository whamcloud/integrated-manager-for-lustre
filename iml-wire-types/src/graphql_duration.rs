// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

#[cfg(feature = "postgres-interop")]
use sqlx::postgres::types::PgInterval;
#[cfg(feature = "graphql")]
use std::convert::TryInto;
use std::{convert::TryFrom, fmt, time::Duration};

#[derive(serde::Deserialize, serde::Serialize, Clone, PartialEq, Debug)]
#[serde(try_from = "String", into = "String")]
pub struct GraphQLDuration(pub Duration);

#[cfg(feature = "graphql")]
#[juniper::graphql_scalar(
    name = "Duration",
    description = "Duration in human-readable form, like '15min 2ms'"
)]
impl<S> GraphQLScalar for GraphQLDuration
where
    S: juniper::ScalarValue,
{
    fn resolve(&self) -> juniper::Value {
        juniper::Value::scalar(humantime::format_duration(self.0).to_string())
    }

    fn from_input_value(value: &juniper::InputValue) -> Option<GraphQLDuration> {
        value.as_string_value()?.to_string().try_into().ok()
    }

    fn from_str<'a>(value: juniper::ScalarToken<'a>) -> juniper::ParseScalarResult<'a, S> {
        <String as juniper::ParseScalarValue<S>>::from_str(value)
    }
}

#[cfg(feature = "postgres-interop")]
impl From<PgInterval> for GraphQLDuration {
    fn from(x: PgInterval) -> Self {
        GraphQLDuration(Duration::from_micros(x.microseconds as u64))
    }
}

impl TryFrom<String> for GraphQLDuration {
    type Error = humantime::DurationError;

    fn try_from(x: String) -> Result<Self, Self::Error> {
        x.parse::<humantime::Duration>()
            .map(|x| GraphQLDuration(x.into()))
    }
}

impl From<GraphQLDuration> for String {
    fn from(x: GraphQLDuration) -> Self {
        x.to_string()
    }
}

impl fmt::Display for GraphQLDuration {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "{}", humantime::format_duration(self.0).to_string())
    }
}
