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
use iml_wire_types::snapshot::Snapshot;
use std::collections::HashMap;

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

fn mk_snapshot(mut m: HashMap<String, String>) -> Result<Snapshot, &'static str> {
    let filesystem_name = m.remove("filesystem_name").ok_or("filesystem_name")?;
    let snapshot_name = m.remove("snapshot_name").ok_or("snapshot_name")?;
    let snapshot_fsname = m.remove("snapshot_fsname").ok_or("snapshot_fsname")?;
    let modify_time_s = m.remove("modify_time").ok_or("modify_time")?;
    let create_time_s = m.remove("create_time").ok_or("create_time")?;
    let status = m.remove("status").ok_or("status")?;
    let comment = m.remove("comment");

    let modify_time = parse_date(modify_time_s)?;
    let create_time = parse_date(create_time_s)?;
    let mounted = match status.as_str() {
        "mounted" => Some(true),
        "not mount" => Some(false),
        "unknown" => None,
        _ => return Err("mounted, not mount, unknown"),
    };

    Ok(Snapshot {
        filesystem_name,
        snapshot_name,
        comment,
        create_time,
        snapshot_fsname,
        modify_time,
        mounted,
    })
}

fn map<I>() -> impl Parser<I, Output = Snapshot>
where
    I: Stream<Token = char>,
    I::Error: ParseError<I::Token, I::Range, I::Position>,
{
    char::spaces()
        .with(many1(attempt(entry())))
        .skip(char::spaces())
        .and_then(|m: HashMap<String, String>| {
            mk_snapshot(m).map_err(StreamErrorFor::<I>::expected_static_message)
        })
}

pub(crate) fn parse<I>() -> impl Parser<I, Output = Vec<Snapshot>>
where
    I: Stream<Token = char>,
    I::Error: ParseError<I::Token, I::Range, I::Position>,
{
    many1(map())
}

#[cfg(test)]
mod test {
    use chrono::offset::TimeZone;
    use chrono::offset::Utc;
    use combine::EasyParser;
    use iml_wire_types::snapshot::Snapshot;

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
                filesystem_name: "zfsmo".into(),
                snapshot_name: "bar".into(),
                comment: None,
                create_time: Utc.ymd(2020, 8, 7).and_hms(16, 43, 06),
                snapshot_fsname: "16c3a547".into(),
                modify_time: Utc.ymd(2020, 8, 7).and_hms(16, 43, 06),
                mounted: Some(false),
            },
            Snapshot {
                filesystem_name: "zfsmo".into(),
                snapshot_name: "foo".into(),
                comment: Some("hello world".into()),
                create_time: Utc.ymd(2020, 8, 7).and_hms(16, 29, 30),
                snapshot_fsname: "6f27d503".into(),
                modify_time: Utc.ymd(2020, 8, 7).and_hms(17, 29, 30),
                mounted: Some(true),
            },
        ];

        assert_eq!(super::parse().easy_parse(sample), Ok((snaps, "")));
    }
}
