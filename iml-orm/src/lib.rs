// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

#![recursion_limit = "256"]

#[cfg(feature = "postgres-interop")]
#[macro_use]
pub extern crate diesel;

#[cfg(feature = "postgres-interop")]
pub mod models;

#[cfg(feature = "postgres-interop")]
pub mod schema;

#[cfg(feature = "postgres-interop")]
pub mod profile;

#[cfg(feature = "postgres-interop")]
pub mod repo;

pub mod sfa;

#[cfg(feature = "postgres-interop")]
use futures::channel::oneshot;
#[cfg(feature = "postgres-interop")]
use thiserror::Error;

#[cfg(feature = "postgres-interop")]
use diesel::{
    query_builder::QueryFragment,
    query_dsl::load_dsl::ExecuteDsl,
    r2d2::{ConnectionManager, Pool},
    PgConnection,
};
#[cfg(feature = "postgres-interop")]
use iml_manager_env::get_db_conn_string;
#[cfg(feature = "postgres-interop")]
use tokio_diesel::AsyncRunQueryDsl;

#[cfg(feature = "postgres-interop")]
pub trait PgQueryFragment: QueryFragment<diesel::pg::Pg> {}

#[cfg(feature = "postgres-interop")]
impl<T> PgQueryFragment for T where T: QueryFragment<diesel::pg::Pg> {}

#[cfg(feature = "postgres-interop")]
pub trait AsyncRunQueryDslPostgres: AsyncRunQueryDsl<diesel::PgConnection, DbPool> {}

#[cfg(feature = "postgres-interop")]
impl<T> AsyncRunQueryDslPostgres for T where T: AsyncRunQueryDsl<diesel::PgConnection, DbPool> {}

#[cfg(feature = "postgres-interop")]
/// Allows for a generic return type for Insert statements, that can be used in either a sync or async
/// context.
pub trait Executable:
    RunQueryDsl<diesel::PgConnection> + ExecuteDsl<diesel::PgConnection, diesel::pg::Pg>
{
}

#[cfg(feature = "postgres-interop")]
impl<T> Executable for T where
    T: RunQueryDsl<diesel::PgConnection> + ExecuteDsl<diesel::PgConnection, diesel::pg::Pg>
{
}

#[cfg(feature = "postgres-interop")]
pub type DbPool = Pool<ConnectionManager<diesel::PgConnection>>;

#[cfg(feature = "postgres-interop")]
pub use diesel::query_dsl::RunQueryDsl;

#[cfg(feature = "postgres-interop")]
pub use tokio_diesel;

#[cfg(feature = "postgres-interop")]
pub use r2d2;

#[derive(Debug, Error)]
#[cfg(feature = "postgres-interop")]
pub enum ImlOrmError {
    #[error(transparent)]
    R2D2Error(#[from] r2d2::Error),
    #[error(transparent)]
    OneshotCanceled(#[from] oneshot::Canceled),
    #[error(transparent)]
    AsyncError(#[from] tokio_diesel::AsyncError),
}

#[cfg(feature = "postgres-interop")]
/// Get a new connection pool based on the envs connection string.
pub fn pool() -> Result<DbPool, ImlOrmError> {
    let manager = ConnectionManager::<PgConnection>::new(get_db_conn_string());

    Pool::builder()
        .build(manager)
        .map_err(ImlOrmError::R2D2Error)
}

mod change {
    use std::{
        cmp::{Eq, Ord},
        collections::BTreeSet,
        fmt::Debug,
        iter::FromIterator,
    };

    pub trait Identifiable {
        type Id: Eq + Ord;

        fn id(&self) -> Self::Id;
    }

    pub trait Changeable: Eq + Ord + Debug {}

    impl<T> Changeable for T where T: Eq + Ord + Debug {}

    #[derive(Debug)]
    pub struct Upserts<T: Changeable>(pub Vec<T>);

    #[derive(Debug)]
    pub struct Deletions<T: Changeable>(pub Vec<T>);

    type Changes<'a, T> = (Option<Upserts<&'a T>>, Option<Deletions<&'a T>>);

    pub trait GetChanges<T: Changeable + Identifiable> {
        /// Given new and old items, this method compares them and
        /// returns a tuple of `Upserts` and `Deletions`.
        fn get_changes<'a>(&'a self, old: &'a Self) -> Changes<'a, T>;
    }

    impl<T: Changeable + Identifiable> GetChanges<T> for Vec<T> {
        fn get_changes<'a>(&'a self, old: &'a Self) -> Changes<'a, T> {
            let new = BTreeSet::from_iter(self);
            let old = BTreeSet::from_iter(old);

            let to_upsert: Vec<&T> = new.difference(&old).copied().collect();

            let to_upsert = if to_upsert.is_empty() {
                None
            } else {
                Some(Upserts(to_upsert))
            };

            let new_ids: BTreeSet<<T as Identifiable>::Id> = new.iter().map(|x| x.id()).collect();
            let old_ids: BTreeSet<<T as Identifiable>::Id> = old.iter().map(|x| x.id()).collect();

            let changed: BTreeSet<_> = new_ids.intersection(&old_ids).collect();

            let to_remove: Vec<&T> = old
                .difference(&new)
                .filter(|x| {
                    let id = x.id();

                    changed.get(&id).is_none()
                })
                .copied()
                .collect();

            let to_remove = if to_remove.is_empty() {
                None
            } else {
                Some(Deletions(to_remove))
            };

            (to_upsert, to_remove)
        }
    }
}

pub use change::*;
