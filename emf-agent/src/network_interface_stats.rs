// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use combine::{
    error::ParseError,
    many1,
    parser::char::{char, digit, letter, spaces},
    stream::Stream,
    token, Parser,
};
use emf_wire_types::{InterfaceStats, RxStats, StatResult, TxStats};
use std::{collections::HashMap, convert::TryFrom, num::ParseIntError};

pub type InterfaceStatsMap = HashMap<String, InterfaceStats>;

fn interface<I>() -> impl Parser<I, Output = String>
where
    I: Stream<Token = char>,
    I::Error: ParseError<I::Token, I::Range, I::Position>,
{
    many1(letter().or(digit()).or(token('@')))
}

fn parse_interface<I>() -> impl Parser<I, Output = String>
where
    I: Stream<Token = char>,
    I::Error: ParseError<I::Token, I::Range, I::Position>,
{
    spaces()
        .and(many1(interface()))
        .map(|x| x.1)
        .skip(char(':'))
}

fn parse_stat<I>() -> impl Parser<I, Output = StatResult>
where
    I: Stream<Token = char>,
    I::Error: ParseError<I::Token, I::Range, I::Position>,
{
    spaces()
        .and(many1(digit()).map(|x: String| x.parse::<u64>()))
        .map(|x| x.1)
}

fn parse_stats<I>() -> impl Parser<
    I,
    Output = (
        StatResult,
        StatResult,
        StatResult,
        StatResult,
        StatResult,
        StatResult,
        StatResult,
        StatResult,
    ),
>
where
    I: Stream<Token = char>,
    I::Error: ParseError<I::Token, I::Range, I::Position>,
{
    spaces()
        .and(parse_stat())
        .and(parse_stat())
        .and(parse_stat())
        .and(parse_stat())
        .and(parse_stat())
        .and(parse_stat())
        .and(parse_stat())
        .and(parse_stat())
        .map(|((((((((_, x1), x2), x3), x4), x5), x6), x7), x8)| (x1, x2, x3, x4, x5, x6, x7, x8))
}

fn parse_stats_line<I>() -> impl Parser<I, Output = (String, Result<InterfaceStats, ParseIntError>)>
where
    I: Stream<Token = char>,
    I::Error: ParseError<I::Token, I::Range, I::Position>,
{
    parse_interface()
        .and(parse_stats())
        .and(parse_stats())
        .map(|((interface, rx), tx)| {
            let rx_stats = RxStats::try_from(rx);
            let tx_stats = TxStats::try_from(tx);

            (interface, InterfaceStats::try_from((rx_stats, tx_stats)))
        })
}

pub fn parse(output: &str) -> Result<InterfaceStatsMap, ParseIntError> {
    output
        .split('\n')
        .skip(2)
        .filter_map(|x| parse_stats_line().parse(x).ok())
        .try_fold(
            InterfaceStatsMap::new(),
            |mut acc, ((interface, stats), _)| match stats {
                Ok(stats) => {
                    let parts: Vec<&str> = interface.split('@').collect();
                    acc.insert(parts[0].to_string(), stats);

                    Ok(acc)
                }
                Err(e) => Err(e),
            },
        )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_interface() {
        let result = parse_stats_line()
            .parse("eth0: 72453387   55109    0    0    0     0          0         0   630390    9575    0    0    0     0       0          0")
            .map(|((interface, _), _)| interface);

        assert_eq!(result, Ok("eth0".to_string()));
    }

    #[test]
    fn test_parse_interface_stats() {
        let result = parse_stats_line()
            .parse("eth0: 72453387   55109    0    0    0     0          0         0   630390    9575    0    0    0     0       0          0")
            .map(|((_, stats), _)| stats);

        assert_eq!(
            result,
            Ok(Ok(InterfaceStats {
                rx: RxStats {
                    bytes: 72453387,
                    packets: 55109,
                    errs: 0,
                    drop: 0,
                    fifo: 0,
                    frame: 0,
                    compressed: 0,
                    multicast: 0
                },
                tx: TxStats {
                    bytes: 630390,
                    packets: 9575,
                    errs: 0,
                    drop: 0,
                    fifo: 0,
                    colls: 0,
                    carrier: 0,
                    compressed: 0
                }
            }))
        );
    }

    #[test]
    fn test_parse() {
        let stats_data = include_bytes!("./fixtures/network_stats.txt");
        let stats_data = std::str::from_utf8(stats_data).unwrap();
        let stats = parse(stats_data).unwrap();

        insta::with_settings!({sort_maps => true}, {
            insta::assert_json_snapshot!(stats)
        });
    }
}
