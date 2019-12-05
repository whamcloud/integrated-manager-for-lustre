// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::error::Error;
use futures::future::try_join_all;
use iml_postgres::Client;
use iml_wire_types::{
    db::{FsRecord, ManagedOstRecord, ManagedTargetRecord, Name, OstPoolOstsRecord, OstPoolRecord},
    Fqdn,
};
use std::sync::Arc;

pub struct PoolClient {
    client: Arc<Client>,
    fqdn: String,
    pool_type_id: i32,
}

impl Clone for PoolClient {
    fn clone(&self) -> Self {
        PoolClient {
            client: Arc::clone(&self.client),
            fqdn: self.fqdn.clone(),
            pool_type_id: self.pool_type_id,
        }
    }
}

pub async fn connect(fqdn: Fqdn) -> Result<PoolClient, Error> {
    let (client, conn) = iml_postgres::connect().await?;

    tokio::spawn(async move {
        conn.await
            .unwrap_or_else(|e| tracing::error!("DB connection error {}", e));
    });

    let query = format!(
        "SELECT id FROM django_content_type WHERE app_label = 'chroma_core' AND model = $1"
    );
    let s = client.prepare(&query).await?;
    let row = client.query_one(&s, &[&"ostpool"]).await?;
    let pool_type_id = row.try_get(0)?;

    Ok(PoolClient {
        client: Arc::new(client),
        fqdn: fqdn.to_string(),
        pool_type_id,
    })
}

impl PoolClient {
    /// Assume that if there is a single filesystem with a given name,
    /// that it's the correct one
    pub async fn fsid(&self, fsname: &str) -> Result<i32, Error> {
        let query = format!(
            "SELECT id FROM {} WHERE name=$1 AND not_deleted=True",
            FsRecord::table_name()
        );
        let s = self.client.prepare(&query).await?;
        let vr = self.client.query(&s, &[&fsname]).await.map_err(|e| {
            tracing::error!("fs2id({}): Query failed: {}: {}", fsname, query, e);
            e
        })?;

        match vr.len() {
            0 => Err(Error::NotFound),
            1 => vr[0].try_get(0).map_err(|e| Error::Postgres(e)),
            _ => {
                tracing::error!("Multiple filesystems named {} found", fsname);
                // @@ check fqdn managedhost -> managedtargetmount -> managedtarget -> filesystem
                Err(Error::NotFound)
            }
        }
    }

    pub async fn poolid(&self, fsid: i32, pn: &str) -> Result<Option<i32>, Error> {
        let query = format!(
            "SELECT id FROM {} WHERE name=$1 AND filesystem_id=$2 AND not_deleted=True",
            OstPoolRecord::table_name()
        );
        let s = self.client.prepare(&query).await?;
        match self.client.query_one(&s, &[&pn, &fsid]).await {
            Ok(row) => row.try_get(0).map(Some).map_err(|e| {
                tracing::error!("poolid({}.{}): {}", fsid, pn, e);
                Error::Postgres(e)
            }),
            Err(e) => {
                tracing::debug!("poolid({}.{}): {}", fsid, pn, e);
                Ok(None)
            }
        }
    }

    async fn ostid(&self, fsid: i32, ost: &str) -> Result<Option<i32>, Error> {
        let query = format!(
            "SELECT managedtarget_ptr_id FROM {} AS MO INNER JOIN {} AS MT ON MO.managedtarget_ptr_id = MT.id WHERE filesystem_id = $1 AND name = $2 AND not_deleted=True",
            ManagedOstRecord::table_name(),
            ManagedTargetRecord::table_name());
        let s = self.client.prepare(&query).await?;
        match self.client.query_one(&s, &[&fsid, &ost]).await {
            Ok(row) => row.try_get(0).map(Some).or_else(|e| {
                tracing::error!("ostid({}, {}): {}", fsid, ost, e);
                tracing::debug!("ostid:query: {}", query);
                Ok(None)
            }),
            Err(e) => {
                tracing::error!("ostid({}, {}): {}", fsid, ost, e);
                Ok(None)
            }
        }
    }

    pub async fn create(&self, fsid: i32, pn: &str) -> Result<i32, Error> {
        let query = format!(
            "INSERT INTO {} (name, content_type_id, filesystem_id, not_deleted) VALUES ($1, $2, $3, 't') RETURNING id",
            OstPoolRecord::table_name()
        );
        let s = self.client.prepare(&query).await?;

        match self
            .client
            .query_one(&s, &[&pn, &self.pool_type_id, &fsid])
            .await
        {
            Ok(row) => row.try_get(0).map_err(|e| Error::Postgres(e)),
            Err(e) => Err(Error::Postgres(e)),
        }
    }

    pub async fn delete(&self, fsid: i32, pn: &str) -> Result<(), Error> {
        let query = format!(
            "UPDATE {} SET not_deleted = NULL WHERE filesystem = $1 AND name = $2",
            OstPoolRecord::table_name()
        );
        let s = self.client.prepare(&query).await?;

        self.client
            .execute(&s, &[&fsid, &pn])
            .await
            .map(drop)
            .map_err(|e| Error::Postgres(e))
    }

    pub async fn grow(&self, fsid: i32, poolid: i32, osts: &Vec<String>) -> Result<(), Error> {
        let query = format!(
            "INSERT INTO {} (ostpool_id, managedost_id) VALUES ($1, $2)",
            OstPoolOstsRecord::table_name()
        );
        let s = self.client.prepare(&query).await?;

        let xs = osts.iter().map(|o| {
            let s = s.clone();
            async move {
                if let Some(ostid) = self.ostid(fsid, &o).await? {
                    tracing::debug!("Growing ({}).({}): ost:{}({})", fsid, poolid, o, ostid);
                    self.client
                        .execute(&s, &[&poolid, &ostid])
                        .await
                        .map(drop)
                        .map_err(|e| Error::Postgres(e))
                } else {
                    tracing::warn!("Failed Grow ({}).({}): ost:{} missing", fsid, poolid, o);
                    Ok(())
                }
            }
        });
        try_join_all(xs).await?;
        Ok(())
    }

    pub async fn shrink(&self, fsid: i32, poolid: i32, osts: &Vec<String>) -> Result<(), Error> {
        let query = format!(
            "DELETE FROM {} WHERE ostpool_id = $1 AND managedost_id = $2",
            OstPoolOstsRecord::table_name(),
        );
        let s = self.client.prepare(&query).await?;

        let xs = osts.iter().map(|o| {
            let s = s.clone();
            async move {
                if let Some(ostid) = self.ostid(fsid, &o).await? {
                    tracing::debug!("Shrinking ({}).({}): ost:{}({})", fsid, poolid, o, ostid);
                    self.client
                        .execute(&s, &[&ostid, &poolid])
                        .await
                        .map(drop)
                        .map_err(|e| {
                            tracing::error!(
                                "shrink(({}).({}), {}({})) failed: {}",
                                fsid,
                                poolid,
                                o,
                                ostid,
                                e
                            );
                            Error::Postgres(e)
                        })
                } else {
                    tracing::warn!("Failed Shrink ({}).({}): ost:{} missing", fsid, poolid, o);
                    Ok(())
                }
            }
        });
        try_join_all(xs).await?;
        Ok(())
    }
}
