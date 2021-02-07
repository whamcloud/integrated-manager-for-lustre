// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{error::EmfApiError, graphql::Context};
use emf_postgres::sqlx;
use emf_wire_types::Host;
use futures::TryFutureExt;

pub(crate) struct HostQuery;

#[juniper::graphql_object(Context = Context)]
impl HostQuery {
    /// List all known `Host` records.
    async fn list(context: &Context) -> juniper::FieldResult<Vec<Host>> {
        let xs = sqlx::query_as!(Host, "SELECT * FROM host")
            .fetch_all(&context.pg_pool)
            .err_into::<EmfApiError>()
            .await?;

        Ok(xs)
    }
}
