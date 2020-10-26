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
    let mut svcs: HashMap<SnapshotPolicy, AbortHandle> = HashMap::new();
    tracing::info!("starting automatic snapshot job");
    loop {
        tracing::trace!("fetching current policies");
        let resp: iml_graphql_queries::Response<snapshot::policy::list::Resp> =
            graphql(client.clone(), snapshot::policy::list::build()).await?;

        let new: HashSet<SnapshotPolicy> = Result::from(resp)?
            .data
            .snapshot
            .policies
            .into_iter()
            .collect();
        tracing::trace!("current policies: {:?}", new);

        let old: HashSet<SnapshotPolicy> = svcs.keys().cloned().collect();
        tracing::trace!("previous policies: {:?}", old);

        for p in old.difference(&new) {
            tracing::debug!("stopping obsolete {:?}", p);
            let ah = svcs.remove(p).unwrap();
            ah.abort();
        }
        for p in new.difference(&old).cloned() {
            tracing::debug!("starting new {:?}", p);
            let ah = start(client.clone(), pg.clone(), p.clone());
            svcs.insert(p, ah);
        }

        tokio::time::delay_for(tokio::time::Duration::from_secs(10)).await;
    }
}

fn start(client: Client, pg: PgPool, policy: SnapshotPolicy) -> AbortHandle {
    let (ah, ah_reg) = AbortHandle::new_pair();

    tokio::spawn(Abortable::new(
        async move {
            loop {
                if let Err(e) = run(&client, &pg, &policy).await {
                    tracing::warn!("automatic snapshot failed: {}", e);
                    tokio::time::delay_for(tokio::time::Duration::from_secs(10)).await;
                }
            }
        },
        ah_reg,
    ));

    ah
}

async fn run(client: &Client, pg: &PgPool, policy: &SnapshotPolicy) -> Result<(), Error> {
    let interval = Duration::from_std(policy.interval.0).unwrap();

    let mut next_time = Utc::now();

    if let Some(start) = policy.start {
        let next_time = next_tick(start, policy.interval.0, next_time);
        tracing::debug!(
            "next automatic snapshot of {} will be at {:?}",
            policy.filesystem,
            next_time
        );
    } else {
        let latest = sqlx::query!(
            r#"
                SELECT snapshot_name, create_time FROM snapshot
                WHERE filesystem_name = $1 AND snapshot_name LIKE '\_\_%'
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
            next_time = x.create_time + interval;
        }
    }

    let pause =
        Duration::to_std(&(next_time - Utc::now())).unwrap_or(std::time::Duration::from_secs(0));

    if pause.as_secs() > 0 {
        tracing::debug!(
            "sleeping {:?} before creating next snapshot of {}",
            pause,
            policy.filesystem
        );
        tokio::time::delay_for(pause).await;
    }

    let mut snapshots = sqlx::query!(
        r#"
            SELECT snapshot_name, create_time FROM snapshot
            WHERE filesystem_name = $1
        "#,
        policy.filesystem
    )
    .fetch_all(pg)
    .await?
    .into_iter()
    .map(|x| (x.create_time, x.snapshot_name))
    .collect::<Vec<_>>();

    if snapshots.len() < policy.keep as usize {
        let new = create_snapshot(client, pg, policy).await?;
        snapshots.push(new);
    } else {
        tracing::warn!(
            "cannot create new automatic snapshot: too many snapshots exist ({}, max: {})",
            snapshots.len(),
            policy.keep
        );
    }

    let obsolete = get_obsolete(policy, snapshots);

    if obsolete.is_empty() {
        tracing::info!("no obsolete snapshots of {}", policy.filesystem);
    } else {
        destroy_snapshots(client, pg, policy, obsolete).await?;
    }

    // XXX Wait in hope that the new changes are reflected in the database:
    let pause = Duration::to_std(&(next_time + interval - Utc::now()))
        .unwrap_or(std::time::Duration::from_secs(0))
        .div_f32(2.0);

    if pause.as_secs() > 0 {
        tracing::debug!(
            "cooldown sleeping {:?} before creating next snapshot of {}",
            pause,
            policy.filesystem
        );
        tokio::time::delay_for(pause).await;
    }

    Ok(())
}

async fn create_snapshot(
    client: &Client,
    pg: &PgPool,
    policy: &SnapshotPolicy,
) -> Result<(DateTime<Utc>, String), Error> {
    let now = Utc::now();
    let name = now.format("__%s").to_string();
    tracing::info!(
        "creating automatic snapshot {} of {}",
        name,
        policy.filesystem
    );

    let query = snapshot::create::build(
        policy.filesystem.clone(),
        name.clone(),
        "automatic snapshot".into(),
        Some(policy.barrier),
    );
    let resp: iml_graphql_queries::Response<snapshot::create::Resp> =
        graphql(client.clone(), query).await?;
    let x = Result::from(resp)?.data.snapshot.create;
    wait_for_cmds_success(&[x], None).await?;

    sqlx::query!(
        "UPDATE snapshot_policy SET last_run = $1 WHERE filesystem = $2",
        Utc::now(),
        policy.filesystem
    )
    .execute(pg)
    .await?;

    Ok((now, name))
}

async fn destroy_snapshots(
    client: &Client,
    pg: &PgPool,
    policy: &SnapshotPolicy,
    snapshots: Vec<String>,
) -> Result<(), Error> {
    let cmd_futs: Vec<_> = snapshots
        .iter()
        .map(|x| destroy_snapshot(client.clone(), policy.filesystem.clone(), x.clone()))
        .collect();
    let cmds = try_join_all(cmd_futs).await?;
    wait_for_cmds_success(&cmds, None).await?;

    tracing::info!("destroyed obsolete snapshots: {}", snapshots.join(","));

    sqlx::query!(
        "UPDATE snapshot_policy SET last_run = $1 WHERE filesystem = $2",
        Utc::now(),
        policy.filesystem
    )
    .execute(pg)
    .await?;

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
    let cmd = Result::from(resp)?.data.snapshot.destroy;
    Ok(cmd)
}

fn get_obsolete(
    policy: &SnapshotPolicy,
    mut snapshots: Vec<(DateTime<Utc>, String)>,
) -> Vec<String> {
    snapshots.sort_unstable_by_key(|x| std::cmp::Reverse(x.0));
    tracing::debug!("all snapshots of {}: {:?}", policy.filesystem, snapshots);

    let mut tail: Vec<_> = snapshots.iter().map(|x| x.0).collect();

    let mut to_delete: Vec<DateTime<Utc>> = Vec::with_capacity(tail.len());

    fn collect(d: &mut Vec<DateTime<Utc>>, res: LinkedList<LinkedList<NaiveDateTime>>) {
        for x in res {
            for y in x.into_iter().skip(1) {
                d.push(DateTime::from_utc(y, Utc));
            }
        }
    }

    // Handle daily snapshots:
    if let Some(x) = tail.get(0) {
        let next_day = x.date().succ().and_hms(0, 0, 0);
        let cut = next_day - Duration::days(policy.daily as i64);

        let (daily, new_tail): (Vec<_>, Vec<_>) = tail.into_iter().partition(|x| *x > cut);
        tracing::debug!("daily snapshots to consider: {:?}, {:?}", cut, daily);

        let datetimes: Vec<NaiveDateTime> = daily.iter().map(|x| x.naive_utc()).collect();
        let res = partition_datetime(
            &|_| Duration::days(1).num_seconds(),
            next_day.naive_utc(),
            &datetimes,
        );
        tracing::debug!("daily partition: {:?}", res);
        collect(&mut to_delete, res);
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
        tracing::debug!("weekly snapshots to consider: {:?}, {:?}", cut, weekly);

        let datetimes: Vec<NaiveDateTime> = weekly.iter().map(|x| x.naive_utc()).collect();
        let res = partition_datetime(
            &|_| Duration::weeks(1).num_seconds(),
            next_week.naive_utc(),
            &datetimes,
        );
        tracing::debug!("weekly partition: {:?}", res);
        collect(&mut to_delete, res);
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
        collect(&mut to_delete, res);
        tail = new_tail;
    }
    tracing::debug!(
        "snapshots of {} to consider for deletion after the monthly schedule: {:?}",
        policy.filesystem,
        tail
    );

    to_delete.append(&mut tail);

    to_delete.sort_unstable();
    let (mut delete, mut keep): (Vec<_>, Vec<_>) = snapshots
        .into_iter()
        .partition(|x| to_delete.binary_search(&x.0).is_ok() && x.1.starts_with("__"));
    tracing::debug!("snapshots of {} to keep: {:?}", policy.filesystem, keep);

    let excess = keep.len() as i32 - policy.keep;
    if excess >= 0 {
        keep.sort_unstable_by_key(|x| x.0);
        let mut more = keep
            .into_iter()
            .filter(|x| x.1.starts_with("__"))
            .take(1 + excess as usize) // +1 to have a slot for the next snapshot
            .collect();
        tracing::debug!(
            "extra snapshots of {} to delete to keep the number below {}: {:?}",
            policy.filesystem,
            policy.keep,
            more
        );
        delete.append(&mut more);
    } else if excess < -1 {
        // if there is still some room, keep as many snapshots as possible
        let n = std::cmp::max(0, delete.len() as i32 + 1 - excess.abs());
        delete.sort_unstable_by_key(|x| x.0);
        let more: Vec<_> = delete.drain(n as usize..).collect();
        tracing::debug!(
            "extra snapshots of {} to keep because there are still free slots: {:?}",
            policy.filesystem,
            more
        );
    }

    delete.into_iter().map(|x| x.1).collect()
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

fn next_tick(
    start: DateTime<Utc>,
    interval: std::time::Duration,
    now: DateTime<Utc>,
) -> DateTime<Utc> {
    if now > start {
        let d = (now - start).num_seconds();
        let i = Duration::from_std(interval).unwrap().num_seconds();
        let one = if d % i == 0 { 0 } else { 1 };
        let n = (d / i) + one;
        now + Duration::seconds(n * i - d)
    } else {
        start
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::Duration;
    use iml_wire_types::graphql_duration::GraphQLDuration;

    fn to_datetime(s: &str) -> DateTime<Utc> {
        DateTime::parse_from_rfc3339(s).unwrap().with_timezone(&Utc)
    }

    fn snapshots(x: Vec<(&str, &str)>) -> Vec<(DateTime<Utc>, String)> {
        x.into_iter()
            .map(|(t, n)| {
                (
                    DateTime::parse_from_rfc3339(t).unwrap().with_timezone(&Utc),
                    n.into(),
                )
            })
            .collect()
    }

    #[test]
    fn test_ticks() {
        for (start, interval, now, res) in vec![
            (
                "2020-12-15T00:00:00Z",
                Duration::hours(12),
                "2020-12-15T04:00:00Z",
                "2020-12-15T12:00:00Z",
            ),
            (
                "2020-12-25T01:23:45Z",
                Duration::hours(2),
                "2020-12-25T01:00:00Z",
                "2020-12-25T01:23:45Z",
            ),
            (
                "2020-12-25T01:23:45Z",
                Duration::hours(2),
                "2020-12-25T01:30:00Z",
                "2020-12-25T03:23:45Z",
            ),
            (
                "2020-12-15T20:00:00Z",
                Duration::days(1),
                "2020-12-15T20:00:00Z",
                "2020-12-15T20:00:00Z",
            ),
            (
                "2002-12-25T01:00:00Z",
                Duration::hours(1),
                "2020-12-15T01:01:00Z",
                "2020-12-15T02:00:00Z",
            ),
        ]
        .into_iter()
        .map(|(p, i, n, r)| {
            (
                to_datetime(p),
                i.to_std().unwrap(),
                to_datetime(n),
                to_datetime(r),
            )
        }) {
            assert_eq!(next_tick(start, interval, now), res);
        }
    }

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
            let start = to_datetime(d0).naive_utc();
            let end = to_datetime(d).naive_utc();

            assert_eq!(add_month(&start, n), end);
        }
    }

    #[test]
    fn test_get_obsolete_less() {
        let policy = SnapshotPolicy {
            id: 0,
            filesystem: "fs".into(),
            interval: GraphQLDuration(std::time::Duration::from_secs(60)),
            start: None,
            barrier: true,
            keep: 5,
            daily: 0,
            weekly: 0,
            monthly: 0,
            last_run: None,
        };

        let snapshots = snapshots(vec![
            ("2020-11-24T14:34:11Z", "__01"),
            ("2020-11-24T14:33:00Z", "02"),
            ("2020-11-24T04:30:00Z", "__03"),
            ("2020-11-23T04:36:12Z", "__04"),
            ("2020-11-23T04:34:00Z", "__05"),
            ("2020-11-23T01:30:00Z", "__06"),
        ]);

        let mut obsolete = get_obsolete(&policy, snapshots);
        obsolete.sort();

        let expected_obsolete: Vec<String> =
            vec!["__05", "__06"].into_iter().map(String::from).collect();

        assert_eq!(obsolete, expected_obsolete);
    }

    #[test]
    fn test_get_obsolete_automatic_only() {
        let policy = SnapshotPolicy {
            id: 0,
            filesystem: "fs".into(),
            interval: GraphQLDuration(std::time::Duration::from_secs(60)),
            start: None,
            barrier: true,
            keep: 11,
            daily: 4,
            weekly: 3,
            monthly: 3,
            last_run: None,
        };

        let snapshots = snapshots(vec![
            ("2020-11-24T14:34:11Z", "__01"),
            ("2020-11-24T14:33:00Z", "__02"),
            ("2020-11-24T04:30:00Z", "__03"),
            ("2020-11-23T04:36:12Z", "__04"),
            ("2020-11-23T04:34:00Z", "__05"),
            ("2020-11-23T01:30:00Z", "__06"),
            ("2020-11-22T21:38:13Z", "__07"),
            ("2020-11-22T16:32:00Z", "__08"),
            ("2020-11-22T03:33:00Z", "__09"),
            ("2020-11-21T23:22:14Z", "__10"),
            ("2020-11-21T11:59:00Z", "__11"),
            ("2020-11-17T00:59:21Z", "__12"),
            ("2020-11-14T23:22:22Z", "__13"),
            ("2020-11-14T11:59:00Z", "__14"),
            ("2020-11-13T09:44:00Z", "__15"),
            ("2020-11-13T08:37:00Z", "__16"),
            ("2020-11-12T05:11:00Z", "__17"),
            ("2020-11-06T23:11:23Z", "__18"),
            ("2020-11-05T13:55:00Z", "__19"),
            ("2020-11-01T13:11:31Z", "__20"),
            ("2020-10-31T10:55:32Z", "__21"),
            ("2020-10-31T00:55:00Z", "__22"),
            ("2020-10-23T00:55:00Z", "__23"),
            ("2020-10-01T00:01:00Z", "__24"),
            ("2020-09-21T00:00:33Z", "__25"),
        ]);

        let mut obsolete = get_obsolete(&policy, snapshots);
        obsolete.sort();

        let expected_obsolete: Vec<String> = vec![
            "__02", "__03", "__05", "__06", "__08", "__09", "__11", "__14", "__15", "__16", "__17",
            "__19", "__22", "__23", "__24",
        ]
        .into_iter()
        .map(String::from)
        .collect();

        assert_eq!(obsolete, expected_obsolete);
    }

    #[test]
    fn test_get_obsolete_mixed() {
        let policy = SnapshotPolicy {
            id: 0,
            filesystem: "fs".into(),
            interval: GraphQLDuration(std::time::Duration::from_secs(60)),
            start: None,
            barrier: true,
            keep: 10,
            daily: 4,
            weekly: 3,
            monthly: 3,
            last_run: None,
        };

        let snapshots = snapshots(vec![
            ("2020-11-24T14:34:11Z", "__01"),
            ("2020-11-24T14:33:00Z", "02"),
            ("2020-11-24T04:30:00Z", "__03"),
            ("2020-11-23T04:36:12Z", "__04"),
            ("2020-11-23T04:34:00Z", "__05"),
            ("2020-11-23T01:30:00Z", "__06"),
            ("2020-11-22T21:38:13Z", "__07"),
            ("2020-11-22T16:32:00Z", "__08"),
            ("2020-11-22T03:33:00Z", "09"),
            ("2020-11-21T23:22:14Z", "__10"),
            ("2020-11-21T11:59:00Z", "__11"),
            ("2020-11-17T00:59:21Z", "__12"),
            ("2020-11-14T23:22:22Z", "__13"),
            ("2020-11-14T11:59:00Z", "__14"),
            ("2020-11-13T09:44:00Z", "__15"),
            ("2020-11-13T08:37:00Z", "__16"),
            ("2020-11-12T05:11:00Z", "__17"),
            ("2020-11-06T23:11:23Z", "__18"),
            ("2020-11-05T13:55:00Z", "__19"),
            ("2020-11-01T13:11:31Z", "__20"),
            ("2020-10-31T10:55:32Z", "__21"),
            ("2020-10-31T00:55:00Z", "__22"),
            ("2020-10-23T00:55:00Z", "__23"),
            ("2020-10-01T00:01:00Z", "__24"),
            ("2020-09-21T00:00:33Z", "25"),
        ]);

        let mut obsolete = get_obsolete(&policy, snapshots);
        obsolete.sort();

        let expected_obsolete: Vec<String> = vec![
            "__03", "__05", "__06", "__08", "__11", "__14", "__15", "__16", "__17", "__18", "__19",
            "__20", "__21", "__22", "__23", "__24",
        ]
        .into_iter()
        .map(String::from)
        .collect();

        assert_eq!(obsolete, expected_obsolete);
    }

    #[test]
    fn test_get_obsolete_more() {
        let policy = SnapshotPolicy {
            id: 0,
            filesystem: "fs".into(),
            interval: GraphQLDuration(std::time::Duration::from_secs(60)),
            start: None,
            barrier: true,
            keep: 4,
            daily: 4,
            weekly: 3,
            monthly: 3,
            last_run: None,
        };

        let snapshots = snapshots(vec![
            ("2020-11-24T14:34:11Z", "__01"),
            ("2020-11-24T14:33:00Z", "02"),
            ("2020-11-24T04:30:00Z", "__03"),
            ("2020-11-23T04:36:12Z", "__04"),
            ("2020-11-23T04:34:00Z", "__05"),
            ("2020-11-23T01:30:00Z", "__06"),
            ("2020-11-22T21:38:13Z", "__07"),
            ("2020-11-22T16:32:00Z", "__08"),
            ("2020-11-22T03:33:00Z", "09"),
            ("2020-11-21T23:22:14Z", "__10"),
            ("2020-11-21T11:59:00Z", "__11"),
            ("2020-11-17T00:59:21Z", "__12"),
            ("2020-11-14T23:22:22Z", "__13"),
            ("2020-11-14T11:59:00Z", "__14"),
            ("2020-11-13T09:44:00Z", "__15"),
            ("2020-11-13T08:37:00Z", "__16"),
            ("2020-11-12T05:11:00Z", "__17"),
            ("2020-11-06T23:11:23Z", "__18"),
            ("2020-11-05T13:55:00Z", "__19"),
            ("2020-11-01T13:11:31Z", "__20"),
            ("2020-10-31T10:55:32Z", "__21"),
            ("2020-10-31T00:55:00Z", "__22"),
            ("2020-10-23T00:55:00Z", "__23"),
            ("2020-10-01T00:01:00Z", "__24"),
            ("2020-09-21T00:00:33Z", "25"),
        ]);

        let mut obsolete = get_obsolete(&policy, snapshots);
        obsolete.sort();

        let expected_obsolete: Vec<String> = vec![
            "__01", "__03", "__04", "__05", "__06", "__07", "__08", "__10", "__11", "__12", "__13",
            "__14", "__15", "__16", "__17", "__18", "__19", "__20", "__21", "__22", "__23", "__24",
        ]
        .into_iter()
        .map(String::from)
        .collect();

        assert_eq!(obsolete, expected_obsolete);
    }
}
