// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file

use crate::input_document::{InputDocument, Step};
use std::collections::HashMap;

pub type JobGraph = petgraph::graph::DiGraph<Step, ()>;

pub fn build_job_graphs(input_doc: InputDocument) -> HashMap<String, JobGraph> {
    input_doc
        .jobs
        .into_iter()
        .map(|(job_name, job)| {
            let g = job
                .steps
                .into_iter()
                .fold((JobGraph::new(), None), |(mut g, last), step| {
                    let node_idx = g.add_node(step);

                    if let Some(last_idx) = last {
                        g.add_edge(last_idx, node_idx, ());
                    };

                    (g, Some(node_idx))
                })
                .0;

            (job_name, g)
        })
        .collect()
}
