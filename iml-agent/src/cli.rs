// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use exitcode;
use futures::Future;
use iml_agent::action_plugins::manage_stratagem;
use prettytable::{cell, row, Table};
use std::process;
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
}

fn run_cmd<R: Send + 'static, E: Send + 'static>(
    fut: impl Future<Item = R, Error = E> + Send + 'static,
) -> std::result::Result<R, E> {
    tokio::runtime::Runtime::new().unwrap().block_on_all(fut)
}

fn main() {
    env_logger::init();

    let _matches = App::from_args();
}
