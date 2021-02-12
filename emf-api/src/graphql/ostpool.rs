// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{error::EmfApiError, graphql::Context};
use emf_wire_types::OstPoolGraphql;
use futures::TryFutureExt;

pub(crate) struct OstPoolQuery;

#[juniper::graphql_object(Context = Context)]
impl OstPoolQuery {
    /// List all known `OstPool` records.
    /// Optionall filter by `fsname` or `poolname`
    async fn list(
        context: &Context,
        fsname: Option<String>,
        poolname: Option<String>,
    ) -> juniper::FieldResult<Vec<OstPoolGraphql>> {
        let xs = sqlx::query_as!(
            OstPoolGraphql,
            r#"
            SELECT
                o.id,
                o.name,
                f.name AS filesystem,
                array_agg((
                    SELECT DISTINCT t.name FROM target t
                    INNER JOIN ostpool_osts oo ON oo.ostpool_id = o.id
                    WHERE t.id = oo.ost_id
                )) AS "osts!"
            FROM ostpool o
            INNER JOIN filesystem f ON f.id = o.filesystem_id
            WHERE ($1::text IS NULL OR f.name = $1)
            AND ($2::text IS NULL OR o.name = $2)
            GROUP BY o.id, f.name
        "#,
            fsname,
            poolname
        )
        .fetch_all(&context.pg_pool)
        .err_into::<EmfApiError>()
        .await?;

        Ok(xs)
    }
}
