// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use chrono::offset::Utc;
use chrono::DateTime;
use combine::{
    attempt, choice, eof,
    error::{ParseError, StreamError},
    many1,
    parser::{char, repeat::take_until},
    satisfy, skip_many,
    stream::{Stream, StreamErrorFor},
    Parser,
};
use iml_wire_types::snapshot::{Detail, Snapshot, Status};
use std::collections::HashMap;

#[derive(PartialEq, Debug)]
enum Segment {
    Snapshot(Snapshot),
    Detail(Detail),
}

fn spaces<I>() -> impl Parser<I, Output = ()>
where
    I: Stream<Token = char>,
    I::Error: ParseError<I::Token, I::Range, I::Position>,
{
    skip_many(satisfy(|c| c == ' ' || c == '\t'))
}

fn eol<I>() -> impl Parser<I, Output = ()>
where
    I: Stream<Token = char>,
    I::Error: ParseError<I::Token, I::Range, I::Position>,
{
    spaces().skip(choice((char::newline().map(|_| ()), eof())))
}

fn whitespace<I>() -> impl Parser<I, Output = ()>
where
    I: Stream<Token = char>,
    I::Error: ParseError<I::Token, I::Range, I::Position>,
{
    skip_many(combine::parser::char::space())
}

fn delimiter<I>() -> impl Parser<I, Output = ()>
where
    I: Stream<Token = char>,
    I::Error: ParseError<I::Token, I::Range, I::Position>,
{
    spaces().skip(char::char(':').skip(spaces()))
}

fn entry<I>() -> impl Parser<I, Output = (String, String)>
where
    I: Stream<Token = char>,
    I::Error: ParseError<I::Token, I::Range, I::Position>,
{
    (
        spaces()
            .with(take_until(attempt(delimiter().or(eol()))))
            .skip(delimiter()),
        take_until(attempt(eol())).skip(eol()),
    )
}

fn parse_date(mut s: String) -> Result<DateTime<Utc>, &'static str> {
    // Can't parse without a timezone.
    // lctl does not print timezone, but uses gettimeofday()
    // to get the time and ctime() to print it.
    s.push_str(" +00:00");
    DateTime::parse_from_str(&s, "%a %b %e %T %Y %#z")
        .map(|t| t.with_timezone(&Utc))
        .map_err(|_| "date string like 'Fri Aug  7 16:43:06 2020'")
}

fn mk_detail(mut m: HashMap<String, String>) -> Result<Detail, &'static str> {
    let fsname = m.remove("snapshot_fsname").ok_or("snapshot_fsname")?;
    let modify_time_s = m.remove("modify_time").ok_or("modify_time")?;
    let create_time_s = m.remove("create_time").ok_or("create_time")?;
    let status_s = m.remove("status").ok_or("status")?;
    let comment = m.remove("comment");
    let role = m.remove("snapshot_role");

    let modify_time = parse_date(modify_time_s)?;
    let create_time = parse_date(create_time_s)?;
    let status = match status_s.as_str() {
        "mounted" => Some(Status::Mounted),
        "not mount" => Some(Status::NotMounted),
        _ => None,
    };
    Ok(Detail {
        role,
        fsname,
        modify_time,
        create_time,
        status,
        comment,
    })
}

fn mk_snapshot(mut m: HashMap<String, String>) -> Result<Snapshot, &'static str> {
    let fsname = m.remove("filesystem_name").ok_or("filesystem_name")?;
    let name = m.remove("snapshot_name").ok_or("snapshot_name")?;
    let details = if m.is_empty() {
        vec![]
    } else {
        vec![mk_detail(m)?]
    };
    Ok(Snapshot {
        fsname,
        name,
        details,
    })
}

fn map<I>() -> impl Parser<I, Output = Segment>
where
    I: Stream<Token = char>,
    I::Error: ParseError<I::Token, I::Range, I::Position>,
{
    whitespace()
        .with(many1(attempt(entry())))
        .skip(whitespace())
        .and_then(|m: HashMap<String, String>| {
            if m.get("filesystem_name").is_some() {
                mk_snapshot(m)
                    .map(Segment::Snapshot)
                    .map_err(StreamErrorFor::<I>::expected_static_message)
            } else if m.get("snapshot_role").is_some() {
                mk_detail(m)
                    .map(Segment::Detail)
                    .map_err(StreamErrorFor::<I>::expected_static_message)
            } else {
                Err(StreamErrorFor::<I>::expected_static_message(
                    "snapshot or snapshot detail",
                ))
            }
        })
}

pub(crate) fn parse<I>() -> impl Parser<I, Output = Vec<Snapshot>>
where
    I: Stream<Token = char>,
    I::Error: ParseError<I::Token, I::Range, I::Position>,
{
    many1(map()).and_then(|ss: Vec<Segment>| {
        let mut it = ss.iter();
        let s = it.next().unwrap();
        if let Segment::Snapshot(snap) = s {
            let (s, mut v) = it.fold((snap.clone(), vec![]), |(mut snap, mut v), s| {
                match s {
                    Segment::Snapshot(sn) => {
                        v.push(snap);
                        snap = sn.clone();
                    }
                    Segment::Detail(d) => {
                        snap.details.push(d.clone());
                    }
                }
                (snap, v)
            });
            v.push(s);
            Ok(v)
        } else {
            Err(StreamErrorFor::<I>::expected_static_message("snapshot"))
        }
    })
}

#[cfg(test)]
mod test {
    use chrono::offset::TimeZone;
    use chrono::offset::Utc;
    use combine::EasyParser;
    use iml_wire_types::snapshot::{Detail, Snapshot, Status};

    #[test]
    fn parse_date() {
        let r = super::parse_date("Fri Aug  7 16:43:06 2020".to_string());
        assert_eq!(r, Ok(Utc.ymd(2020, 8, 7).and_hms(16, 43, 06)));
    }

    #[test]
    fn parse_simple() {
        // white space is intentional:
        let sample = r#"

filesystem_name: zfsmo
    snapshot_name  : bar
    snapshot_fsname: 16c3a547
    create_time: Fri Aug  7 16:43:06 2020
    modify_time: Fri Aug  7 16:43:06 2020
    status: not mount



        filesystem_name: zfsmo
        snapshot_name: foo
        create_time: Fri Aug  7 16:29:30 2020
        modify_time: Fri Aug  7 17:29:30 2020
        snapshot_fsname: 6f27d503
        comment: hello world
        status: mounted

        "#;

        let snaps = vec![
            Snapshot {
                fsname: "zfsmo".into(),
                name: "bar".into(),
                details: vec![Detail {
                    comment: None,
                    create_time: Utc.ymd(2020, 8, 7).and_hms(16, 43, 06),
                    fsname: "16c3a547".into(),
                    modify_time: Utc.ymd(2020, 8, 7).and_hms(16, 43, 06),
                    role: None,
                    status: Some(Status::NotMounted),
                }],
            },
            Snapshot {
                fsname: "zfsmo".into(),
                name: "foo".into(),
                details: vec![Detail {
                    comment: Some("hello world".into()),
                    create_time: Utc.ymd(2020, 8, 7).and_hms(16, 29, 30),
                    fsname: "6f27d503".into(),
                    modify_time: Utc.ymd(2020, 8, 7).and_hms(17, 29, 30),
                    role: None,
                    status: Some(Status::Mounted),
                }],
            },
        ];

        assert_eq!(super::parse().easy_parse(sample), Ok((snaps, "")));
    }

    #[test]
    fn parse_detailed() {
        let sample = r#"
filesystem_name: zfsmo
snapshot_name: bar

snapshot_role: MGS
modify_time: Fri Aug  7 16:43:06 2020
create_time: Fri Aug  7 16:43:06 2020
snapshot_fsname: 16c3a547
status: not mount

filesystem_name: zfsmo
snapshot_name: foo

snapshot_role: MGS
comment: hello world
modify_time: Fri Aug  7 16:29:30 2020
create_time: Fri Aug  7 16:29:30 2020
snapshot_fsname: 6f27d503
status: not mount

snapshot_role: MDT0000
create_time: Fri Aug  7 16:29:30 2020
modify_time: Fri Aug  7 16:29:30 2020
snapshot_fsname: 6f27d503
comment: hello world
status: not mount
        "#;

        let snaps = vec![
            Snapshot {
                fsname: "zfsmo".into(),
                name: "bar".into(),
                details: vec![Detail {
                    comment: None,
                    create_time: Utc.ymd(2020, 8, 7).and_hms(16, 43, 06),
                    fsname: "16c3a547".into(),
                    modify_time: Utc.ymd(2020, 8, 7).and_hms(16, 43, 06),
                    role: Some("MGS".into()),
                    status: Some(Status::NotMounted),
                }],
            },
            Snapshot {
                fsname: "zfsmo".into(),
                name: "foo".into(),
                details: vec![
                    Detail {
                        comment: Some("hello world".into()),
                        create_time: Utc.ymd(2020, 8, 7).and_hms(16, 29, 30),
                        fsname: "6f27d503".into(),
                        modify_time: Utc.ymd(2020, 8, 7).and_hms(16, 29, 30),
                        role: Some("MGS".into()),
                        status: Some(Status::NotMounted),
                    },
                    Detail {
                        comment: Some("hello world".into()),
                        create_time: Utc.ymd(2020, 8, 7).and_hms(16, 29, 30),
                        fsname: "6f27d503".into(),
                        modify_time: Utc.ymd(2020, 8, 7).and_hms(16, 29, 30),
                        role: Some("MDT0000".into()),
                        status: Some(Status::NotMounted),
                    },
                ],
            },
        ];

        assert_eq!(super::parse().easy_parse(sample), Ok((snaps, "")));
    }
}
