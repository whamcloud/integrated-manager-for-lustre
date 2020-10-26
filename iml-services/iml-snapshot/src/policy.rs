// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::Error;
use chrono::{DateTime, Datelike as _, Duration, NaiveDate, NaiveDateTime, Utc};
use futures::future::{try_join_all, AbortHandle, Abortable};
use iml_command_utils::wait_for_cmds_success;
use iml_graphql_queries::snapshot;
use iml_manager_client::{graphql, Client};
use iml_postgres::{sqlx, PgPool};
use iml_tracing::tracing;
use iml_wire_types::{snapshot::SnapshotPolicy, Command};
use std::collections::{HashMap, HashSet, LinkedList};

pub async fn main(client: Client, pg: PgPool) -> Result<(), Error> {
    let mut svcs: HashMap<SnapshotPolicy, (AbortHandle, AbortHandle)> = HashMap::new();
    loop {
        let resp: iml_graphql_queries::Response<snapshot::policy::list::Resp> =
            graphql(client.clone(), snapshot::policy::list::build()).await?;

        let new: HashSet<SnapshotPolicy> = Result::from(resp)?
            .data
            .snapshot_policies
            .into_iter()
            .collect();

        let old: HashSet<SnapshotPolicy> = svcs.keys().cloned().collect();

        for p in old.difference(&new) {
            tracing::debug!("Stopping obsolete {:?}", p);
            let (c, d) = svcs.remove(p).unwrap();
            c.abort();
            d.abort();
        }
        for p in new.difference(&old).cloned() {
            tracing::debug!("Starting new {:?}", p);
            let ah = start(client.clone(), pg.clone(), p.clone());
            svcs.insert(p, ah);
        }

        tokio::time::delay_for(tokio::time::Duration::from_secs(6)).await;
    }
}

fn start(client: Client, pg: PgPool, policy: SnapshotPolicy) -> (AbortHandle, AbortHandle) {
    let (create, create_reg) = AbortHandle::new_pair();
    let (destroy, destroy_reg) = AbortHandle::new_pair();

    let client_1 = client.clone();
    let pg_1 = pg.clone();
    let policy_1 = policy.clone();
    tokio::spawn(Abortable::new(
        async move {
            loop {
                if let Err(e) = create_snapshot(&client_1, &pg_1, &policy_1).await {
                    tracing::warn!("automatic snapshot failed: {}", e);
                    tokio::time::delay_for(tokio::time::Duration::from_secs(10)).await;
                }
            }
        },
        create_reg,
    ));

    tokio::spawn(Abortable::new(
        async move {
            loop {
                if let Err(e) = destroy_obsolete(&client, &pg, &policy).await {
                    tracing::warn!("obsolete snapshot destroying: {}", e);
                    tokio::time::delay_for(tokio::time::Duration::from_secs(10)).await;
                }
            }
        },
        destroy_reg,
    ));

    (create, destroy)
}

async fn create_snapshot(
    client: &Client,
    pg: &PgPool,
    policy: &SnapshotPolicy,
) -> Result<(), Error> {
    let latest = sqlx::query!(
        r#"
            SELECT snapshot_name, create_time FROM snapshot
            WHERE filesystem_name = $1
            AND   snapshot_name LIKE '\_\_%'
            ORDER BY create_time DESC
            LIMIT 1
        "#,
        policy.filesystem
    )
    .fetch_optional(pg)
    .await?;

    if let Some(x) = latest {
        tracing::debug!(
            "latest automatic snapshot of {}: {} at {:?}",
            policy.filesystem,
            x.snapshot_name,
            x.create_time
        );
        let pause = Duration::to_std(&(Utc::now() - x.create_time))
            .ok()
            .and_then(|y| policy.interval.0.checked_sub(y))
            .unwrap_or(std::time::Duration::from_secs(0));

        if pause.as_secs() > 0 {
            tracing::debug!(
                "sleeping {:?} before creating next snapshot of {}",
                pause,
                policy.filesystem
            );
            tokio::time::delay_for(pause).await;
        }
    }

    let time = Utc::now();
    let name = time.format("__%s");
    tracing::info!(
        "creating automatic snapshot {} of {}",
        name,
        policy.filesystem
    );

    let query = snapshot::create::build(
        policy.filesystem.clone(),
        name,
        "automatic snapshot".into(),
        Some(policy.barrier),
    );
    let resp: iml_graphql_queries::Response<snapshot::create::Resp> =
        graphql(client.clone(), query).await?;
    let x = Result::from(resp)?.data.create_snapshot;
    wait_for_cmds_success(&[x], None).await?;

    sqlx::query!(
        "UPDATE snapshot_policy SET last_run = $1 WHERE filesystem = $2",
        time,
        policy.filesystem
    )
    .execute(pg)
    .await?;

    // XXX This is need to make sure the new snapshot is registered.
    // XXX Might need to registered snapshots right after creation (not relying on polling).
    let cooldown = policy.interval.0.div_f64(2.0);
    tracing::debug!("cooldown sleeping {:?} for {}", cooldown, policy.filesystem);
    tokio::time::delay_for(cooldown).await;

    Ok(())
}

async fn destroy_obsolete(
    client: &Client,
    pg: &PgPool,
    policy: &SnapshotPolicy,
) -> Result<(), Error> {
    let snapshots = sqlx::query!(
        r#"
            SELECT snapshot_name, create_time FROM snapshot
            WHERE filesystem_name = $1
            AND   snapshot_name LIKE '\_\_%'
            ORDER BY create_time DESC
        "#,
        policy.filesystem
    )
    .fetch_all(pg)
    .await?
    .into_iter()
    .map(|x| (x.create_time, x.snapshot_name))
    .collect::<Vec<_>>();

    let obsolete = get_obsolete(policy, snapshots);

    if !obsolete.is_empty() {
        let cmd_futs: Vec<_> = obsolete
            .iter()
            .map(|x| destroy_snapshot(client.clone(), policy.filesystem.clone(), x.clone()))
            .collect();
        let cmds = try_join_all(cmd_futs).await?;
        wait_for_cmds_success(&cmds, None).await?;

        tracing::info!("destroyed obsolete snapshots: {}", obsolete.join(","));

        sqlx::query!(
            "UPDATE snapshot_policy SET last_run = $1 WHERE filesystem = $2",
            Utc::now(),
            policy.filesystem
        )
        .execute(pg)
        .await?;
    } else {
        tracing::info!("no obsolete snapshots of {}", policy.filesystem);
    }

    let cooldown = policy.interval.0.div_f64(2.0);
    tracing::debug!(
        "sleeping {:?} before next search for obsolete snapshots of {}",
        cooldown,
        policy.filesystem
    );
    tokio::time::delay_for(cooldown).await;

    Ok(())
}

async fn destroy_snapshot(
    client: Client,
    filesystem: String,
    snapshot: String,
) -> Result<Command, Error> {
    let query = snapshot::destroy::build(filesystem, snapshot, true);
    let resp: iml_graphql_queries::Response<snapshot::destroy::Resp> =
        graphql(client, query).await?;
    let cmd = Result::from(resp)?.data.destroy_snapshot;
    Ok(cmd)
}

fn get_obsolete(policy: &SnapshotPolicy, snapshots: Vec<(DateTime<Utc>, String)>) -> Vec<String> {
    let mut tail: Vec<_> = snapshots
        .iter()
        .skip(policy.keep as usize)
        .map(|x| x.0)
        .collect();

    tracing::debug!(
        "snapshots of {} to consider for deletion after the latest {}: {:?}",
        policy.filesystem,
        policy.keep,
        tail
    );

    let mut to_delete: Vec<DateTime<Utc>> = Vec::with_capacity(tail.len());

    // Handle daily snapshots:
    if let Some(x) = tail.get(0) {
        let next_day = x.date().succ().and_hms(0, 0, 0);
        let cut = next_day - Duration::days(policy.daily as i64);

        let (daily, new_tail): (Vec<_>, Vec<_>) = tail.into_iter().partition(|x| *x > cut);
        tracing::debug!("daily snapshots to consider: {:?}", daily);

        let datetimes: Vec<NaiveDateTime> = daily.iter().map(|x| x.naive_utc()).collect();
        let res = partition_datetime(
            &|_| Duration::days(1).num_seconds(),
            next_day.naive_utc(),
            &datetimes,
        );
        tracing::debug!("daily partition: {:?}", res);
        for x in res.iter() {
            for y in x.iter().skip(1) {
                to_delete.push(DateTime::from_utc(*y, Utc));
            }
        }
        tail = new_tail;
    }
    tracing::debug!(
        "snapshots of {} to consider for deletion after the daily schedule: {:?}",
        policy.filesystem,
        tail
    );

    // Handle weekly snapshots:
    if let Some(x) = tail.get(0) {
        let date = x.date();
        let days_to_next_week = Duration::days((7 - date.weekday().num_days_from_monday()).into());
        let next_week = (date + days_to_next_week).and_hms(0, 0, 0);
        let cut = next_week - Duration::weeks(policy.weekly as i64);

        let (weekly, new_tail): (Vec<_>, Vec<_>) = tail.into_iter().partition(|x| *x > cut);
        tracing::debug!("weekly snapshots to consider: {:?}", weekly);

        let datetimes: Vec<NaiveDateTime> = weekly.iter().map(|x| x.naive_utc()).collect();
        let res = partition_datetime(
            &|_| Duration::weeks(1).num_seconds(),
            next_week.naive_utc(),
            &datetimes,
        );
        tracing::debug!("weekly partition: {:?}", res);
        for x in res.iter() {
            for y in x.iter().skip(1) {
                to_delete.push(DateTime::from_utc(*y, Utc));
            }
        }
        tail = new_tail;
    }
    tracing::debug!(
        "snapshots of {} to consider for deletion after the weekly schedule: {:?}",
        policy.filesystem,
        tail
    );

    // Handle monthly snapshots:
    if let Some(x) = tail.get(0) {
        let next_month = add_month(&x.naive_utc(), 1);
        let cut = DateTime::<Utc>::from_utc(add_month(&next_month, -policy.monthly), Utc);
        let f = |n: u32| {
            let n_month = add_month(&next_month, 0 - n as i32);
            let n1_month = add_month(&n_month, 1);
            (n1_month - n_month).num_seconds()
        };

        let (monthly, new_tail): (Vec<_>, Vec<_>) = tail.into_iter().partition(|x| *x > cut);
        tracing::debug!("monthly snapshots to consider: {:?}, {:?}", cut, monthly);

        let datetimes: Vec<NaiveDateTime> = monthly.iter().map(|x| x.naive_utc()).collect();
        let res = partition_datetime(&f, next_month, &datetimes);
        tracing::debug!("monthly partition: {:?}", res);
        for x in res.iter() {
            for y in x.iter().skip(1) {
                to_delete.push(DateTime::from_utc(*y, Utc));
            }
        }
        tail = new_tail;
    }
    tracing::debug!(
        "snapshots of {} to consider for deletion after the monthly schedule: {:?}",
        policy.filesystem,
        tail
    );

    to_delete.append(&mut tail);

    to_delete.sort_unstable();
    snapshots
        .into_iter()
        .filter(|x| to_delete.binary_search(&x.0).is_ok())
        .map(|x| x.1)
        .collect()
}

fn add_month(date: &NaiveDateTime, n: i32) -> NaiveDateTime {
    let month = date.date().month() as i32;

    let x = month + n;
    let new_year = date.date().year()
        + if x > 12 {
            x / 12
        } else if x < 0 {
            x / 12 - 1
        } else {
            0
        };

    let x = month + n % 12;
    let new_month = if x > 12 {
        x - 12
    } else if x <= 0 {
        12 + x
    } else {
        x
    } as u32;

    let new_date = NaiveDate::from_ymd(new_year, new_month, 1);

    new_date.and_hms(0, 0, 0)
}

fn partition<I>(f: &dyn Fn(u32) -> i64, v0: i64, v: I) -> LinkedList<LinkedList<i64>>
where
    I: IntoIterator<Item = i64>,
{
    let mut term: LinkedList<i64> = LinkedList::new();
    let mut res: LinkedList<LinkedList<i64>> = LinkedList::new();
    let mut n: u32 = 1;
    let mut a: i64 = v0;

    for i in v {
        while i >= a + f(n) {
            res.push_back(term);
            term = LinkedList::new();
            a += f(n);
            n += 1;
        }
        term.push_back(i);
    }
    res.push_back(term);

    res
}

fn partition_datetime(
    f: &dyn Fn(u32) -> i64,
    start: NaiveDateTime,
    datetimes: &[NaiveDateTime],
) -> LinkedList<LinkedList<NaiveDateTime>> {
    let mut v: Vec<i64> = datetimes
        .into_iter()
        .map(|&d| (start - d).num_seconds())
        .collect();
    v.sort_unstable();
    v.dedup();

    let part = partition(f, 0, v);

    part.into_iter()
        .map(|l| {
            l.into_iter()
                .map(|d| start - Duration::seconds(d))
                .collect()
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::Timelike;
    use iml_wire_types::graphql_duration::GraphQLDuration;

    #[test]
    fn test_add_month() {
        for (d0, n, d) in vec![
            ("2020-11-24T12:34:56Z", 0, "2020-11-01T00:00:00Z"),
            ("2020-10-24T14:35:02Z", 1, "2020-11-01T00:00:00Z"),
            ("2020-11-24T14:35:02Z", 1, "2020-12-01T00:00:00Z"),
            ("2020-01-11T14:34:10Z", 10, "2020-11-01T00:00:00Z"),
            ("2020-12-01T06:34:12Z", 23, "2022-11-01T00:00:00Z"),
            ("2020-03-11T06:34:12Z", 36, "2023-03-01T00:00:00Z"),
            ("2020-10-24T14:35:02Z", -1, "2020-09-01T00:00:00Z"),
            ("2020-12-01T00:00:00Z", -3, "2020-09-01T00:00:00Z"),
            ("2020-10-24T14:35:02Z", -12, "2019-10-01T00:00:00Z"),
            ("2020-10-14T14:35:02Z", -16, "2019-06-01T00:00:00Z"),
            ("2020-09-04T14:35:02Z", -36, "2017-09-01T00:00:00Z"),
        ] {
            let start = DateTime::parse_from_rfc3339(d0)
                .unwrap()
                .with_timezone(&Utc)
                .naive_utc();
            let end = DateTime::parse_from_rfc3339(d)
                .unwrap()
                .with_timezone(&Utc)
                .naive_utc();

            assert_eq!(add_month(&start, n), end);
        }
    }

    #[test]
    fn test_get_obsolete() {
        let policy = SnapshotPolicy {
            id: 0,
            filesystem: "fs".into(),
            interval: GraphQLDuration(std::time::Duration::from_secs(60)),
            barrier: true,
            keep: 2,
            daily: 4,
            weekly: 3,
            monthly: 3,
            last_run: None,
        };

        let snapshots: Vec<(DateTime<Utc>, String)> = vec![
            "2020-11-24T14:36:01Z",
            "2020-11-24T14:35:02Z",
            "2020-11-24T14:34:11Z",
            "2020-11-24T14:33:00Z",
            "2020-11-24T04:30:00Z",
            "2020-11-23T04:36:12Z",
            "2020-11-23T04:34:00Z",
            "2020-11-23T01:30:00Z",
            "2020-11-22T21:38:13Z",
            "2020-11-22T16:32:00Z",
            "2020-11-22T03:33:00Z",
            "2020-11-21T23:22:14Z",
            "2020-11-21T11:59:00Z",
            "2020-11-17T00:59:21Z",
            "2020-11-14T23:22:22Z",
            "2020-11-14T11:59:00Z",
            "2020-11-13T09:44:00Z",
            "2020-11-13T08:37:00Z",
            "2020-11-12T05:11:00Z",
            "2020-11-06T23:11:23Z",
            "2020-11-05T13:55:00Z",
            "2020-11-01T13:11:31Z",
            "2020-10-31T10:55:32Z",
            "2020-10-31T00:55:00Z",
            "2020-10-23T00:55:00Z",
            "2020-10-01T00:01:00Z",
            "2020-09-21T00:00:33Z",
        ]
        .into_iter()
        .map(|t| {
            (
                DateTime::parse_from_rfc3339(t).unwrap().with_timezone(&Utc),
                t.into(),
            )
        })
        .collect();

        let expected_number_of_obsolete = snapshots
            .iter()
            .filter(|x| x.0.time().second() == 0)
            .count();

        let obsolete = get_obsolete(&policy, snapshots);
        let expected_obsolete: Vec<String> = vec![
            "2020-11-24T14:33:00Z",
            "2020-11-24T04:30:00Z",
            "2020-11-23T04:34:00Z",
            "2020-11-23T01:30:00Z",
            "2020-11-22T16:32:00Z",
            "2020-11-22T03:33:00Z",
            "2020-11-21T11:59:00Z",
            "2020-11-14T11:59:00Z",
            "2020-11-13T09:44:00Z",
            "2020-11-13T08:37:00Z",
            "2020-11-12T05:11:00Z",
            "2020-11-05T13:55:00Z",
            "2020-10-31T00:55:00Z",
            "2020-10-23T00:55:00Z",
            "2020-10-01T00:01:00Z",
        ]
        .into_iter()
        .map(String::from)
        .collect();

        assert_eq!(obsolete, expected_obsolete);
        assert_eq!(obsolete.len(), expected_number_of_obsolete);
    }
}
