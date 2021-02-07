// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{error::EmfApiError, graphql::Context};
use emf_postgres::sqlx;
use emf_wire_types::Filesystem;
use futures::TryFutureExt;

pub(crate) struct FilesystemQuery;

#[juniper::graphql_object(Context = Context)]
impl FilesystemQuery {
    /// List all known `Filesystem` records.
    async fn list(context: &Context) -> juniper::FieldResult<Vec<Filesystem>> {
        let xs = sqlx::query_as!(Filesystem, "SELECT * FROM filesystem")
            .fetch_all(&context.pg_pool)
            .err_into::<EmfApiError>()
            .await?;

        Ok(xs)
    }
    /// Fetch a filesystem by name
    async fn by_name(context: &Context, name: String) -> juniper::FieldResult<Option<Filesystem>> {
        let x = sqlx::query_as!(
            Filesystem,
            "SELECT * FROM filesystem where name = $1",
            &name
        )
        .fetch_optional(&context.pg_pool)
        .err_into::<EmfApiError>()
        .await?;

        Ok(x)
    }
}
