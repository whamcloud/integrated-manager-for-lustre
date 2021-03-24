// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file

use crate::{state_schema::Schema, TransitionGraph};
use emf_wire_types::ComponentType;
use std::collections::{BTreeMap, BTreeSet, HashMap};

pub(crate) fn build_transition_graphs(schema: &Schema) -> BTreeMap<ComponentType, TransitionGraph> {
    schema
        .components
        .iter()
        .filter_map(
            |(comp_name, component)| -> Option<(ComponentType, TransitionGraph)> {
                let states: BTreeSet<_> = component.states.keys().collect();

                let mut graph = TransitionGraph::new();
                let mut node_map: HashMap<_, petgraph::graph::NodeIndex> = HashMap::new();
                for state in states {
                    let node_index = graph.add_node(*state);
                    node_map.insert(state, node_index);
                }

                let connections: BTreeSet<(_, _, _)> = component
                    .actions
                    .iter()
                    .filter_map(|(action_name, action)| {
                        let state = action.state.as_ref()?;

                        let x = if let Some(start_nodes) = state.start.as_ref() {
                            // Create an edge from each start node to the end node
                            let connections: BTreeSet<(_, _, _)> = start_nodes
                                .iter()
                                .map(|x| (x, &state.end, action_name))
                                .collect();

                            connections
                        } else {
                            BTreeSet::new()
                        };

                        Some(x)
                    })
                    .flatten()
                    .collect();

                for (a, b, edge_name) in connections {
                    let a = *node_map.get(&a)?;
                    let b = *node_map.get(&b)?;
                    graph.add_edge(a, b, *edge_name);
                }

                Some((comp_name.to_owned(), graph))
            },
        )
        .collect::<BTreeMap<ComponentType, TransitionGraph>>()
}

#[cfg(test)]
mod tests {
    use super::*;
    use emf_lib_state_machine::state_schema::STATE_SCHEMA;
    use insta::assert_json_snapshot;

    #[test]
    fn parse_schema() {
        let transition_graphs = build_transition_graphs(&STATE_SCHEMA);

        insta::with_settings!({sort_maps => true}, {
            assert_json_snapshot!(transition_graphs);
        });
    }
}
