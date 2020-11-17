// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    snapshot::create_snapshot, snapshot::destroy_snapshot, snapshot::mount_snapshot,
    snapshot::unmount_snapshot, step::Steps, Error,
};
use async_trait::async_trait;
use iml_postgres::{sqlx, PgPool};
use iml_wire_types::{state_machine, state_machine::Transition, warp_drive::RecordId};

#[async_trait]
pub trait Job {
    async fn get_locks(&self, _pool: &PgPool) -> Result<Vec<RecordId>, Error> {
        Ok(vec![])
    }
    /// The steps that need to be run to complete this job.
    /// Steps run serially and can be cancelled.
    /// Cancelling a step cancels all further steps in the series,
    /// and also cancels all dependendant jobs.
    fn get_steps(&self) -> Steps;
    fn get_transition(&self) -> Option<state_machine::Transition> {
        None
    }
}

#[async_trait]
impl Job for state_machine::Job {
    fn get_steps(&self) -> Steps {
        match self.clone() {
            Self::CreateSnapshotJob(x) => Steps::default().add_remote_step(create_snapshot, x),
            Self::MountSnapshotJob(x) => Steps::default().add_remote_step(mount_snapshot, x),
            Self::UnmountSnapshotJob(x) => Steps::default().add_remote_step(unmount_snapshot, x),
            Self::RemoveSnapshotJob(x) => Steps::default().add_remote_step(destroy_snapshot, x),
        }
    }
    fn get_transition(&self) -> Option<state_machine::Transition> {
        match self {
            Self::CreateSnapshotJob(_) => Some(Transition::CreateSnapshot.into()),
            Self::MountSnapshotJob(_) => Some(Transition::MountSnapshot.into()),
            Self::UnmountSnapshotJob(_) => Some(Transition::UnmountSnapshot.into()),
            Self::RemoveSnapshotJob(_) => Some(Transition::RemoveSnapshot.into()),
        }
    }
    async fn get_locks(&self, pool: &PgPool) -> Result<Vec<RecordId>, Error> {
        match self {
            Self::CreateSnapshotJob(_) => Ok(vec![]),
            Self::MountSnapshotJob(x) => {
                let id = get_snapshot_id(pool, &x.name, &x.fsname).await?;

                Ok(vec![RecordId::Snapshot(id)])
            }
            Self::UnmountSnapshotJob(x) => {
                let id = get_snapshot_id(pool, &x.name, &x.fsname).await?;

                Ok(vec![RecordId::Snapshot(id)])
            }
            Self::RemoveSnapshotJob(x) => {
                let id = get_snapshot_id(pool, &x.name, &x.fsname).await?;

                Ok(vec![RecordId::Snapshot(id)])
            }
        }
    }
}

async fn get_snapshot_id(pool: &PgPool, name: &str, fsname: &str) -> Result<i32, Error> {
    let id = sqlx::query!(
        "SELECT id FROM snapshot WHERE snapshot_name = $1 AND filesystem_name = $2",
        name,
        fsname
    )
    .fetch_one(pool)
    .await?
    .id;

    Ok(id)
}
