use combine::{
    error::ParseError,
    many1,
    parser::{
        char::{char, digit, letter, spaces},
    },
    stream::Stream,
    token, Parser,
};
use std::collections::HashMap;

#[derive(Clone, Debug, PartialEq, Eq)]
struct RxStats {
    bytes: u64,
    packets: u64,
    errs: u64,
    drop: u64,
    fifo: u64,
    frame: u64,
    compressed: u64,
    multicast: u64,
}

impl From<(u64, u64, u64, u64, u64, u64, u64, u64)> for RxStats {
    fn from((v1, v2, v3, v4, v5, v6, v7, v8): (u64, u64, u64, u64, u64, u64, u64, u64)) -> Self {
        RxStats {
            bytes: v1,
            packets: v2,
            errs: v3,
            drop: v4,
            fifo: v5,
            frame: v6,
            compressed: v7,
            multicast: v8,
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
struct TxStats {
    bytes: u64,
    packets: u64,
    errs: u64,
    drop: u64,
    fifo: u64,
    colls: u64,
    carrier: u64,
    compressed: u64,
}

impl From<(u64, u64, u64, u64, u64, u64, u64, u64)> for TxStats {
    fn from((v1, v2, v3, v4, v5, v6, v7, v8): (u64, u64, u64, u64, u64, u64, u64, u64)) -> Self {
        TxStats {
            bytes: v1,
            packets: v2,
            errs: v3,
            drop: v4,
            fifo: v5,
            colls: v6,
            carrier: v7,
            compressed: v8,
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct InterfaceStats {
    rx: RxStats,
    tx: TxStats,
}

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

fn parse_stat<I>() -> impl Parser<I, Output = u64>
where
    I: Stream<Token = char>,
    I::Error: ParseError<I::Token, I::Range, I::Position>,
{
    spaces()
        .and(many1(digit()).map(|x: String| x.parse::<u64>().unwrap()))
        .map(|x| x.1)
}

fn parse_stats<I>() -> impl Parser<I, Output = (u64, u64, u64, u64, u64, u64, u64, u64)>
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

fn parse_stats_line<I>() -> impl Parser<I, Output = (String, InterfaceStats)>
where
    I: Stream<Token = char>,
    I::Error: ParseError<I::Token, I::Range, I::Position>,
{
    parse_interface()
        .and(parse_stats())
        .and(parse_stats())
        .map(|((interface, rx), tx)| {
            (
                interface,
                InterfaceStats {
                    rx: rx.into(),
                    tx: tx.into(),
                },
            )
        })
}

pub fn parse(output: &str) -> InterfaceStatsMap {
    output
        .split("\n")
        .skip(2)
        .filter_map(|x| parse_stats_line().parse(x).ok())
        .fold(
            InterfaceStatsMap::new(),
            |mut acc, ((interface, stats), _)| {
                acc.insert(interface, stats);
                acc
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
            .map(|((interface, rx), _)| rx);

        assert_eq!(
            result,
            Ok(InterfaceStats {
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
            })
        );
    }

    #[test]
    fn test_parse() {
        let stats_data = include_bytes!("./fixtures/proc_net_dev.txt");
        let stats_data = std::str::from_utf8(stats_data).unwrap();
        let stats = parse(stats_data);

        insta::assert_debug_snapshot!(stats);
    }
}
