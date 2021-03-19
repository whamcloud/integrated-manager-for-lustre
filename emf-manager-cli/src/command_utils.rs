// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::display_utils::{format_cancelled, format_error, format_success};
use chrono::SecondsFormat;
use console::style;
use emf_wire_types::{CommandGraph, CommandGraphExt as _, CommandPlan, State};
use petgraph::{graph::NodeIndex, visit::Dfs, Direction};
use ptree::{item::StringItem, TreeBuilder};
use std::io;

pub(crate) fn render_command_plan(plan: &CommandPlan) -> io::Result<()> {
    let tree = build_command_plan_tree(&plan);

    ptree::print_tree(&tree)?;

    Ok(())
}

pub(crate) fn render_command_details(plan: &CommandPlan) -> io::Result<()> {
    let roots = plan.externals(Direction::Incoming);

    for root in roots {
        let mut dfs = Dfs::new(plan, root);

        while let Some(nx) = dfs.next(plan) {
            let (job_name, command_job) = &plan[nx];

            println!("Job: {}\n", job_name);
            render_job_details(&command_job);
        }
    }

    Ok(())
}

fn render_job_details(g: &CommandGraph) {
    let mut dfs = Dfs::new(g, NodeIndex::new(0));

    while let Some(nx) = dfs.next(g) {
        let node = &g[nx];

        println!("{}:{}", style("Action").bold(), &node.id);
        println!("{}:{}", style("State").bold(), &node.state);

        if let Some(x) = node.msg.as_ref() {
            match x {
                Ok(x) => {
                    println!("{}: {}", style("Result (Ok)").bold(), x);
                }
                Err(e) => {
                    println!("{}: {}", style("Result (Error)").bold(), e);
                }
            }
        };

        println!(
            "{}:{}",
            style("Started").bold(),
            &node
                .started_at
                .map(|dt| dt.to_rfc3339_opts(SecondsFormat::Millis, true))
                .unwrap_or("---".to_string())
        );
        println!(
            "{}:{}",
            style("Ended").bold(),
            &node
                .finished_at
                .map(|dt| dt.to_rfc3339_opts(SecondsFormat::Millis, true))
                .unwrap_or("---".to_string())
        );
        println!(
            "{}:\n{}\n",
            style("Stdout").bold(),
            style(&node.stdout).dim()
        );
        println!(
            "{}: \n{}\n\n",
            style("Stderr").bold(),
            style(&node.stderr).red()
        );
    }
}

fn build_command_plan_tree(plan: &CommandPlan) -> StringItem {
    let mut tree = TreeBuilder::new("Command".to_string());

    let roots = plan.externals(Direction::Incoming);

    for root in roots {
        let mut dfs = Dfs::new(plan, root);
        let mut depth = 0;

        while let Some(nx) = dfs.next(plan) {
            let (job_name, steps) = &plan[nx];

            let entry = match steps.get_state() {
                State::Pending => format!("... Job: {} pending", job_name),
                State::Running => format!("Job: {} running", job_name),
                State::Completed => format_success(format!("Job: {} completed", job_name)),
                State::Failed => format_error(format!("Job: {} failed", job_name)),
                State::Canceled => format_cancelled(format!("Job: {} cancelled", job_name)),
            };

            tree.begin_child(entry);

            let mut steps_dfs = Dfs::new(steps, NodeIndex::new(0));

            let mut step_depth = 0;

            while let Some(nx) = steps_dfs.next(steps) {
                let step = &steps[nx];
                let d = step
                    .duration()
                    .map(|x| humantime::format_duration(x.into()).to_string())
                    .map(|x| format!(" ({})", x))
                    .unwrap_or_default();

                let entry = match step.state {
                    State::Pending => format!("... Step: {} pending", step.id),
                    State::Running => format!("Step: {} running", step.id),
                    State::Completed => format_success(format!("Step: {} completed{}", step.id, d)),
                    State::Failed => format_error(format!("Step: {} failed{}", step.id, d)),
                    State::Canceled => format_cancelled(format!("Step: {} cancelled", step.id)),
                };

                tree.begin_child(entry);

                step_depth += 1;
            }

            for _ in 0..step_depth {
                tree.end_child();
            }

            depth += 1;
        }

        for _ in 0..depth {
            tree.end_child();
        }
    }

    tree.build()
}

#[cfg(test)]
mod tests {
    use super::build_command_plan_tree;
    use emf_wire_types::{Command, CommandPlan};
    use ptree::write_tree;
    use std::{convert::TryInto, env};

    #[test]
    fn test_plan_tree() -> Result<(), Box<dyn std::error::Error>> {
        // Remove colors from snapshot output
        env::set_var("NO_COLOR", "1");

        let command = include_str!("../fixtures/needs-plan.json");

        let command: Command = serde_json::from_str(command)?;

        let plan: CommandPlan = command.plan.try_into()?;

        let x = build_command_plan_tree(&plan);

        let mut buf = vec![];

        write_tree(&x, &mut buf)?;

        insta::assert_display_snapshot!(String::from_utf8_lossy(&buf));

        Ok(())
    }
}
