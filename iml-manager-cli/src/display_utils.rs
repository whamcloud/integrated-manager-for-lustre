// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use console::{style, Term};
use futures::{Future, FutureExt};
use iml_wire_types::{Command, Host};
use indicatif::ProgressBar;
use prettytable::{Row, Table};
use spinners::{Spinner, Spinners};
use std::fmt::Display;
use structopt::StructOpt;

pub fn wrap_fut<T>(msg: &str, fut: impl Future<Output = T>) -> impl Future<Output = T> {
    let pb = ProgressBar::new_spinner();
    pb.enable_steady_tick(100);
    pb.set_message(msg);

    fut.inspect(move |_| pb.finish_and_clear())
}

pub fn start_spinner(msg: &str) -> impl FnOnce(Option<String>) -> () {
    let sp = Spinner::new(Spinners::Dots9, style(msg).dim().to_string());

    move |msg_opt| match msg_opt {
        Some(msg) => {
            sp.message(msg);
        }
        None => {
            sp.stop();
            if let Err(e) = Term::stdout().clear_line() {
                tracing::debug!("Could not clear current line {}", e);
            };
        }
    }
}

pub fn format_cmd_state(cmd: &Command) -> String {
    if cmd.errored {
        format_error(format!("{} errored", cmd.message))
    } else if cmd.cancelled {
        format_cancelled(&format!("{} cancelled", cmd.message))
    } else {
        format_success(format!("{} successful", cmd.message))
    }
}

pub fn display_cmd_state(cmd: &Command) {
    println!("{}", format_cmd_state(&cmd));
}

pub fn format_cancelled(message: impl Display) -> String {
    format!("🚫 {}", message)
}

pub fn display_cancelled(message: impl Display) {
    println!("{}", format_cancelled(&message));
}

pub fn format_success(message: impl Display) -> String {
    format!("{} {}", style("✔").green(), message)
}

pub fn display_success(message: impl Display) {
    println!("{}", format_success(message))
}

pub fn format_error(message: impl Display) -> String {
    format!("{} {}", style("✗").red(), message)
}

pub fn display_error(message: impl Display) {
    println!("{}", format_error(message))
}

pub fn generate_table<Rows, R>(columns: &[&str], rows: Rows) -> Table
where
    R: IntoIterator,
    R::Item: ToString,
    Rows: IntoIterator<Item = R>,
{
    let mut table = Table::new();

    table.set_titles(Row::from(columns));

    for r in rows {
        table.add_row(Row::from(r));
    }

    table
}

pub trait IntoTable {
    fn into_table(self) -> Table;
}

impl IntoTable for Vec<Host> {
    fn into_table(self) -> Table {
        generate_table(
            &["Id", "FQDN", "State", "Nids"],
            self.into_iter().map(|h| {
                vec![
                    h.id.to_string(),
                    h.fqdn,
                    h.state,
                    h.nids.unwrap_or_default().join(" "),
                ]
            }),
        )
    }
}

pub trait IntoDisplayType {
    fn into_display_type(self, display_type: DisplayType) -> String;
}

impl<T: IntoTable + serde::Serialize> IntoDisplayType for T {
    fn into_display_type(self, display_type: DisplayType) -> String {
        match display_type {
            DisplayType::Json => {
                serde_json::to_string_pretty(&self).expect("Cannot serialize item to JSON")
            }
            DisplayType::Yaml => {
                serde_yaml::to_string(&self).expect("Cannot serialize item to YAML")
            }
            DisplayType::Tabular => self.into_table().to_string(),
        }
    }
}

#[derive(StructOpt, Debug)]
pub enum DisplayType {
    Json,
    Yaml,
    Tabular,
}

impl Default for DisplayType {
    fn default() -> Self {
        Self::Tabular
    }
}
