// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::{Future, FutureExt};
use console::{style, Term};
use iml_wire_types::{
    Command, Filesystem, Host, Job, OstPool, ServerProfile, Step, StratagemConfiguration,
};
use number_formatter::{format_bytes, format_number};
use prettytable::{Row, Table};
use std::{fmt::Display, io, str::FromStr};
use structopt::StructOpt;
use indicatif::ProgressBar;
use spinners::{Spinner, Spinners};

pub fn wrap_fut<T>(msg: &str, fut: impl Future<Output = T>) -> impl Future<Output = T> {
    let pb = ProgressBar::new_spinner();
    pb.enable_steady_tick(100);
    pb.set_message(msg);

    fut.inspect(move |_| pb.finish_and_clear())
}

pub fn start_spinner(msg: &str) -> impl FnOnce(Option<String>) {
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

pub fn format_cmd_state(indent: usize, cmd: &Command) -> String {
    let indent = "  ".repeat(indent);
    indent
        + &if cmd.cancelled {
            format_cancelled(&format!("{} cancelled", cmd.message))
        } else if cmd.errored {
            format_error(format!("{} errored", cmd.message))
        } else if cmd.complete {
            format_success(format!("{} successful", cmd.message))
        } else {
            format_in_progress(&cmd.message)
        }
}

pub fn format_job_state<T>(indent: usize, job: &Job<T>) -> String {
    let indent = "  ".repeat(indent);
    indent
        + &if job.cancelled {
            format_cancelled(&format!("{} cancelled", job.description))
        } else if job.errored {
            format_error(format!("{} errored", job.description))
        } else if job.state == "complete" {
            format_success(format!("{} successful", job.description))
        } else {
            format_in_progress(&job.description)
        }
}

pub fn format_step_state(indent: usize, step: &Step) -> String {
    let indent = "  ".repeat(indent);
    indent
        + &match &step.state[..] {
        "cancelled" => format_cancelled(&format!("{} cancelled", step.class_name)),
        "failed" => format_error(format!("{} errored", step.class_name)),
        "success" => format_success(format!("{} successful", step.class_name)),
        _ /* "incomplete" */ => format_in_progress(&step.class_name),
    }
}

pub fn format_in_progress(message: impl Display) -> String {
    format!("  {}", message)
}

pub fn display_cmd_state(cmd: &Command) {
    println!("{}", format_cmd_state(0, &cmd));
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

pub fn usage(
    free: Option<u64>,
    total: Option<u64>,
    formatter: fn(f64, Option<usize>) -> String,
) -> String {
    match (free, total) {
        (Some(free), Some(total)) => format!(
            "{} / {}",
            formatter(total as f64 - free as f64, Some(0)),
            formatter(total as f64, Some(0))
        ),
        (None, Some(total)) => format!("Calculating ... / {}", formatter(total as f64, Some(0))),
        _ => "Calculating ...".to_string(),
    }
}

pub trait IsEmpty {
    fn is_empty(&self) -> bool;
}

impl<T> IsEmpty for Vec<T> {
    fn is_empty(&self) -> bool {
        self.is_empty()
    }
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

impl IntoTable for Vec<StratagemConfiguration> {
    fn into_table(self) -> Table {
        generate_table(
            &["Id", "Filesystem", "State", "Interval", "Purge", "Report"],
            self.into_iter().map(|x| {
                vec![
                    x.id.to_string(),
                    x.filesystem,
                    x.state,
                    x.interval.to_string(),
                    x.purge_duration.map(|x| x.to_string()).unwrap_or_default(),
                    x.report_duration.map(|x| x.to_string()).unwrap_or_default(),
                ]
            }),
        )
    }
}

impl IntoTable for Vec<OstPool> {
    fn into_table(self) -> Table {
        generate_table(
            &["Filesystem", "Pool Name", "OST Count"],
            self.into_iter()
                .map(|x| vec![x.filesystem, x.name, x.osts.len().to_string()]),
        )
    }
}

impl IntoTable for Vec<Filesystem> {
    fn into_table(self) -> Table {
        generate_table(
            &[
                "Name", "State", "Space", "Inodes", "Clients", "MDTs", "OSTs",
            ],
            self.into_iter().map(|x| {
                vec![
                    x.label,
                    x.state,
                    usage(
                        x.bytes_free.map(|x| x as u64),
                        x.bytes_total.map(|x| x as u64),
                        format_bytes,
                    ),
                    usage(x.files_free, x.files_total, format_number),
                    format!("{}", x.client_count.unwrap_or(0)),
                    x.mdts.len().to_string(),
                    x.osts.len().to_string(),
                ]
            }),
        )
    }
}

impl IntoTable for Vec<ServerProfile> {
    fn into_table(self) -> Table {
        generate_table(
            &["Profile", "Name", "Description"],
            self.into_iter()
                .filter(|x| x.user_selectable)
                .map(|x| vec![x.name, x.ui_name, x.ui_description]),
        )
    }
}

pub trait IntoDisplayType {
    fn into_display_type(self, display_type: DisplayType) -> String;
}

impl<T> IntoDisplayType for T
where
    T: IsEmpty + IntoTable + serde::Serialize,
{
    fn into_display_type(self, display_type: DisplayType) -> String {
        match display_type {
            DisplayType::Json => {
                serde_json::to_string_pretty(&self).expect("Cannot serialize item to JSON")
            }
            DisplayType::Yaml => {
                serde_yaml::to_string(&self).expect("Cannot serialize item to YAML")
            }
            DisplayType::Tabular => {
                if self.is_empty() {
                    "".to_string()
                } else {
                    self.into_table().to_string()
                }
            }
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

impl FromStr for DisplayType {
    type Err = io::Error;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s {
            "json" => Ok(Self::Json),
            "yaml" => Ok(Self::Yaml),
            "tabular" => Ok(Self::Tabular),
            _ => Err(Self::Err::new(
                io::ErrorKind::InvalidInput,
                "Couldn't parse display type.",
            )),
        }
    }
}
