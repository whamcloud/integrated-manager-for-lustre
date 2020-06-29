// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::graphql::Context;
use iml_manager_client::{post, Client, ImlManagerClientError};
use iml_manager_env::get_proxy_url;
use iml_postgres::sqlx;
use iml_wire_types::{
    snapshot::{Destroy, Mount, Unmount},
    state_machine::{Command, CommandRecord, Job, Transition},
    warp_drive::{GraphqlRecordId, RecordId},
};

pub(crate) struct StateMachineMutation;

#[juniper::graphql_object(Context = Context)]
impl StateMachineMutation {
    /// Run a state_machine `Transition` for a given record
    async fn run_transition(
        context: &Context,
        record_id: GraphqlRecordId,
        transition: Transition,
    ) -> juniper::FieldResult<CommandRecord> {
        let record_id = RecordId::from(record_id);

        let xs = get_transition_path(context.http_client.clone(), record_id, transition).await?;

        let mut jobs = vec![];

        for x in xs {
            match (record_id, x) {
                (RecordId::Snapshot(x), Transition::MountSnapshot) => {
                    let x = sqlx::query!(
                        "SELECT filesystem_name, snapshot_name FROM snapshot WHERE id = $1",
                        x
                    )
                    .fetch_one(&context.pg_pool)
                    .await?;

                    jobs.push(Job::MountSnapshotJob(Mount {
                        fsname: x.filesystem_name,
                        name: x.snapshot_name,
                    }));
                }
                (RecordId::Snapshot(x), Transition::UnmountSnapshot) => {
                    let x = sqlx::query!(
                        "SELECT filesystem_name, snapshot_name FROM snapshot WHERE id = $1",
                        x
                    )
                    .fetch_one(&context.pg_pool)
                    .await?;

                    jobs.push(Job::UnmountSnapshotJob(Unmount {
                        fsname: x.filesystem_name,
                        name: x.snapshot_name,
                    }))
                }
                (RecordId::Snapshot(x), Transition::RemoveSnapshot) => {
                    let x = sqlx::query!(
                        "SELECT filesystem_name, snapshot_name FROM snapshot WHERE id = $1",
                        x
                    )
                    .fetch_one(&context.pg_pool)
                    .await?;

                    jobs.push(Job::RemoveSnapshotJob(Destroy {
                        fsname: x.filesystem_name,
                        name: x.snapshot_name,
                        force: true,
                    }))
                }
                _ => {}
            }
        }

        let cmd = Command {
            message: "Running Transition".to_string(),
            jobs,
        };

        let mut url = get_proxy_url();

        url.set_path("state_machine/run_command/");

        let cmd = post(context.http_client.clone(), url.as_str(), cmd)
            .await?
            .error_for_status()?
            .json()
            .await?;

        Ok(cmd)
    }
}

pub(crate) struct StateMachineQuery;

#[juniper::graphql_object(Context = Context)]
impl StateMachineQuery {
    /// Given a record, figure out the possible transitions available for it
    async fn get_transitions(
        context: &Context,
        record_id: GraphqlRecordId,
    ) -> juniper::FieldResult<Vec<Transition>> {
        let mut url = get_proxy_url();

        url.set_path("state_machine/get_transitions/");

        let xs = post(
            context.http_client.clone(),
            url.as_str(),
            RecordId::from(record_id),
        )
        .await?
        .error_for_status()?
        .json()
        .await?;

        Ok(xs)
    }
    /// Given a record and transition, figure out the shortest possible path for that
    /// Record to reach that transition.
    async fn get_transition_path(
        context: &Context,
        record_id: GraphqlRecordId,
        transition: Transition,
    ) -> juniper::FieldResult<Vec<Transition>> {
        let xs = get_transition_path(context.http_client.clone(), record_id, transition).await?;

        Ok(xs)
    }
}

async fn get_transition_path(
    client: Client,
    record_id: impl Into<RecordId>,
    transition: Transition,
) -> Result<Vec<Transition>, ImlManagerClientError> {
    let mut url = get_proxy_url();

    url.set_path("state_machine/get_transition_path/");

    let xs = post(client, url.as_str(), (record_id.into(), transition))
        .await?
        .error_for_status()?
        .json()
        .await?;

    Ok(xs)
}
