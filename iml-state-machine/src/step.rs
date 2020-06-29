// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::Error;
use futures::{future, Future, TryFutureExt};
use iml_postgres::PgPool;
use iml_wire_types::Fqdn;
use std::pin::Pin;

type BoxedFuture =
    Pin<Box<dyn Future<Output = Result<(Fqdn, String, serde_json::Value), Error>> + Send>>;

type Step = Box<dyn Fn(PgPool, Result<serde_json::Value, serde_json::Error>) -> BoxedFuture + Send>;

fn mk_step<T, R, Fut>(f: fn(PgPool, T) -> Fut) -> Step
where
    T: serde::de::DeserializeOwned + serde::Serialize + Send + 'static,
    R: serde::Serialize + Send + 'static,
    Fut: Future<Output = Result<(Fqdn, String, R), Error>> + Send + 'static,
{
    Box::new(move |p, x| {
        let x = match x.and_then(|v| serde_json::from_value(v)) {
            Ok(x) => x,
            Err(e) => {
                return Box::pin(future::err(e.into()));
            }
        };

        let fut = f(p, x);

        let fut = fut.err_into().and_then(|(fqdn, action, x)| async {
            let x = serde_json::to_value(x)?;

            Ok((fqdn, action, x))
        });

        Box::pin(fut)
    })
}

pub struct Steps(pub Vec<(Step, Result<serde_json::Value, serde_json::Error>)>);

impl Default for Steps {
    fn default() -> Self {
        Steps(vec![])
    }
}

impl Steps {
    pub fn add_remote_step<Fut, T, R>(mut self, f: fn(PgPool, T) -> Fut, args: T) -> Self
    where
        T: serde::Serialize + serde::de::DeserializeOwned + Send + 'static,
        R: serde::Serialize + Send + 'static,
        Fut: Future<Output = Result<(Fqdn, String, R), Error>> + Send + 'static,
    {
        self.0.push((mk_step(f), serde_json::to_value(args)));

        self
    }
}
