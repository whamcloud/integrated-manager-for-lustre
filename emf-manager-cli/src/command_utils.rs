// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::display_utils::{format_cancelled, format_error, format_success};
use console::style;
use emf_wire_types::{CommandGraph, CommandPlan, State};
use petgraph::{graph::NodeIndex, visit::Dfs};
use ptree::{PrintConfig, Style, TreeItem};
use std::{borrow::Cow, io};

#[derive(Clone)]
pub(crate) struct CommandTree<'a>(&'a CommandGraph, NodeIndex<u32>);

impl<'a> TreeItem for CommandTree<'a> {
    type Child = Self;

    fn write_self<W: io::Write>(&self, f: &mut W, style: &Style) -> io::Result<()> {
        if let Some(w) = self.0.node_weight(self.1) {
            let d = w
                .duration()
                .map(|x| humantime::format_duration(x.into()).to_string())
                .map(|x| format!(" ({})", x))
                .unwrap_or_default();

            let entry = match w.state {
                State::Pending => format!("... {} pending", w.id),
                State::Running => format!("{} running", w.id),
                State::Completed => format_success(format!("{} completed{}", w.id, d)),
                State::Failed => format_error(format!("{} failed{}", w.id, d)),
                State::Canceled => format_cancelled(format!("{} cancelled", w.id)),
            };

            write!(f, "{}", style.paint(entry))
        } else {
            Ok(())
        }
    }

    fn children(&self) -> Cow<[Self::Child]> {
        let v: Vec<_> = self
            .0
            .neighbors(self.1)
            .map(|i| CommandTree(self.0, i))
            .collect();

        Cow::from(v)
    }
}

pub(crate) fn render_command_plan(plan: &CommandPlan) -> io::Result<()> {
    let cfg = PrintConfig::from_env();

    for (k, g) in plan {
        println!("\nJob: {}\n", style(k).bold());

        ptree::print_tree_with(&CommandTree(&g, NodeIndex::new(0)), &cfg)?;
    }

    for (k, g) in plan {
        println!("\n\nJob Details: {}\n", style(k).bold());
        render_job_details(&g);
    }

    Ok(())
}

fn render_job_details(g: &CommandGraph) {
    let mut dfs = Dfs::new(g, NodeIndex::new(0));

    while let Some(nx) = dfs.next(g) {
        let node = &g[nx];

        println!("Action: {}\n", style(&node.id).bold());
        println!("State: {}\n", style(&node.state).bold());
        println!("Stdout: \n{}\n", style(&node.stdout).dim());
        println!("Stderr: \n{}\n", style(&node.stderr).red());
    }
}
