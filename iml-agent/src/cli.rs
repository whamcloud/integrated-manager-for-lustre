// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::Future;
use iml_agent::action_plugins::manage_stratagem;
use iml_agent::action_plugins::stratagem_action_warning;
use std::fs::File;
use std::io;
use std::io::prelude::*;
use std::io::BufReader;
use std::process::exit;
use structopt::StructOpt;

#[derive(Debug, StructOpt)]
pub enum Command {
    #[structopt(name = "start")]
    /// Start the Stratagem server
    Start,
    #[structopt(name = "stop")]
    /// Stop the Stratagem server
    Stop,
    #[structopt(name = "status")]
    /// Check Stratagem server status
    Status,
    #[structopt(name = "groups")]
    /// Get Stratagem Groups
    Groups,
}

#[derive(Debug, StructOpt)]
pub struct FidInput {
    #[structopt(short = "i")]
    /// File to read from, "-" for stdin, or unspecified for on cli
    input: Option<String>,

    #[structopt(name = "FSNAME")]
    /// Lustre filesystem name, or mountpoint
    fsname: String,

    #[structopt(name = "FIDS")]
    /// Optional list of FIDs to purge
    fidlist: Vec<String>,
}

#[derive(Debug, StructOpt)]
pub enum ActionRunner {
    #[structopt(name = "warning")]
    /// Run warning action
    Warning {
        #[structopt(short = "o")]
        /// File to write to, or "-" or unspecified for stdout
        output: Option<String>,

        #[structopt(flatten)]
        fidopts: FidInput,
    },

    #[structopt(name = "purge")]
    /// Run purge action
    Purge {
        #[structopt(flatten)]
        fidopts: FidInput,
    }
}

#[derive(StructOpt, Debug)]
#[structopt(name = "iml-agent")]
/// The Integrated Manager for Lustre Agent CLI
pub enum App {
    #[structopt(name = "stratagem")]
    /// Work with Stratagem server
    Stratagem {
        #[structopt(subcommand)]
        command: Command,
    },

    #[structopt(name = "action")]
    /// Work with Stratagem server
    Action {
        #[structopt(subcommand)]
        command: ActionRunner,
    },
}

fn run_cmd<R: Send + 'static, E: Send + 'static>(
    fut: impl Future<Item = R, Error = E> + Send + 'static,
) -> std::result::Result<R, E> {
    tokio::runtime::Runtime::new().unwrap().block_on_all(fut)
}

fn input_to_iter(input: Option<String>, fidlist: Vec<String>) -> Box<Iterator<Item = String>> {
    match input {
        None => {
            if fidlist.is_empty() {
                Box::new(
                    BufReader::new(io::stdin())
                        .lines()
                        .map(|x| x.expect("Failed to readline from stdin")),
                )
            } else {
                Box::new(fidlist.into_iter())
            }
        }
        Some(name) => {
            let buf: Box<BufRead> = match name.as_ref() {
                "-" => Box::new(BufReader::new(io::stdin())),
                _ => {
                    let f = match File::open(&name) {
                        Ok(x) => x,
                        Err(e) => {
                            log::error!("Failed to open {}: {}", &name, e);
                            exit(-1);
                        }
                    };
                    Box::new(BufReader::new(f))
                }
            };
            Box::new(
                buf.lines()
                    .map(|x| x.expect("Failed to readline from file")),
            )
        }
    }
}

fn main() {
    env_logger::init();

    let matches = App::from_args();

    match matches {
        App::Action { command: cmd }=> match cmd {
            ActionRunner::Purge{ fidopts: opt } => {
                let device = opt.fsname;
                let input = input_to_iter(opt.input, opt.fidlist);

                if liblustreapi::rmfid(&device, input).is_err() {
                    exit(-1);
                }
            },
            ActionRunner::Warning{ output: out, fidopts: opt } => {
                let device = opt.fsname;
                let output: Box<io::Write> = match out {
                    Some(file) => Box::new(File::create(file).expect("Failed to create file")),
                    None => Box::new(io::stdout()),
                };
                let input = input_to_iter(opt.input, opt.fidlist);

                if stratagem_action_warning::write_records(&device, input, output).is_err() {
                    exit(-1);
                }
            },
        },
        App::Stratagem{ command: _ } => eprintln!("Not Yet Implemented"),
    }
}
