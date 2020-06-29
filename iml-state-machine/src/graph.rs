// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_wire_types::state_machine::{snapshot, Edge, State, Transition};
use petgraph::{
    algo::astar,
    graph::{DiGraph, NodeIndex},
    prelude::*,
    visit::{EdgeFiltered, IntoNeighborsDirected},
    Direction,
};
use std::collections::HashSet;

trait GraphExt<N: Eq + PartialEq, E: Eq + PartialEq> {
    fn find_node_idx(&self, x: &N) -> Option<NodeIndex>;
}

impl<N: Eq + PartialEq, E: Eq + PartialEq> GraphExt<N, E> for Graph<N, E> {
    fn find_node_idx(&self, x: &N) -> Option<NodeIndex> {
        self.node_indices().find(|i| &self[*i] == x)
    }
}

pub type StateGraph = DiGraph<State, Edge>;

pub trait StateGraphExt {
    /// Get the node cooresponding to the current state, if one exists.
    fn get_state_node(&self, state: impl Into<State>) -> Option<NodeIndex>;
    /// Get the available `Transition`s for this NodeIndex.
    ///
    /// A `Transition` is available iff it's cooresponding state
    /// and all dependendant states can be satisfied.
    fn get_available_transitions(&self, n: NodeIndex) -> HashSet<Transition>;
    fn get_transition_path(
        &self,
        start_state: impl Into<State>,
        transition: impl Into<Transition>,
    ) -> Option<Vec<Transition>>;
}

impl StateGraphExt for StateGraph {
    fn get_state_node(&self, state: impl Into<State>) -> Option<NodeIndex> {
        self.find_node_idx(&state.into())
    }
    fn get_available_transitions(&self, n: NodeIndex) -> HashSet<Transition> {
        let graph = EdgeFiltered::from_fn(&self, |x| x.weight().is_transition());

        let mut transitions = HashSet::new();

        let mut dfs = Dfs::new(&graph, n);

        let mut seen = HashSet::new();
        seen.insert(n);

        while let Some(from_node) = dfs.next(&self) {
            let mut neighbors = graph
                .neighbors_directed(from_node, Direction::Outgoing)
                .into_iter();

            while let Some(to_node) = neighbors.next() {
                if seen.contains(&to_node) {
                    continue;
                }

                seen.insert(to_node);

                let ix = self
                    .find_edge(from_node, to_node)
                    .expect("Could not find edge");

                let t = match self[ix] {
                    Edge::Dependency(_) => {
                        panic!("Found a `Dependency` in a `Transition` filtered graph.");
                    }
                    Edge::Transition(t) => t,
                };

                transitions.insert(t);
            }
        }

        transitions
    }
    fn get_transition_path(
        &self,
        start_state: impl Into<State>,
        transition: impl Into<Transition>,
    ) -> Option<Vec<Transition>> {
        let start_state_ix = self.get_state_node(start_state)?;
        let x = transition.into();

        let xs = astar(
            &self,
            start_state_ix,
            |finish| {
                self.edges_directed(finish, Direction::Incoming)
                    .any(|edge| edge.weight() == &Edge::Transition(x))
            },
            |_| 1,
            |_| 0,
        )?
        .1;

        let xs = xs.iter().zip(xs.iter().skip(1)).collect::<Vec<_>>();

        let mut out = vec![];

        for (a, b) in xs {
            let e = self.find_edge(*a, *b)?;

            let edge = *&self[e];

            match edge {
                Edge::Dependency(_) => return None,
                Edge::Transition(x) => out.push(x),
            };
        }

        Some(out)
    }
}

pub fn build_graph() -> StateGraph {
    let mut deps = StateGraph::new();

    let unknown_snapshot = deps.add_node(snapshot::State::Unknown.into());
    let unmounted_snapshot = deps.add_node(snapshot::State::Unmounted.into());
    let mounted_snapshot = deps.add_node(snapshot::State::Mounted.into());
    let removed_snapshot = deps.add_node(snapshot::State::Removed.into());

    deps.add_edge(
        unknown_snapshot,
        unmounted_snapshot,
        Transition::CreateSnapshot.into(),
    );

    deps.add_edge(
        unmounted_snapshot,
        mounted_snapshot,
        Transition::MountSnapshot.into(),
    );

    deps.add_edge(
        mounted_snapshot,
        unmounted_snapshot,
        Transition::UnmountSnapshot.into(),
    );

    deps.add_edge(
        unmounted_snapshot,
        removed_snapshot,
        Transition::RemoveSnapshot.into(),
    );

    deps.add_edge(
        mounted_snapshot,
        removed_snapshot,
        Transition::RemoveSnapshot.into(),
    );

    deps
}

#[cfg(test)]
pub mod test {
    use super::*;
    use iml_wire_types::state_machine::snapshot;
    use petgraph::dot::Dot;

    #[test]
    fn get_snapshot_mount_transitions() {
        let graph = build_graph();

        let ix = graph.get_state_node(snapshot::State::Mounted).unwrap();

        let xs = graph.get_available_transitions(ix);

        assert_eq!(
            xs,
            vec![
                Transition::RemoveSnapshot.into(),
                Transition::UnmountSnapshot.into(),
            ]
            .into_iter()
            .collect()
        );
    }

    #[test]
    fn get_snapshot_unmount_transitions() {
        let graph = build_graph();

        let ix = graph.get_state_node(snapshot::State::Unmounted).unwrap();

        let xs = graph.get_available_transitions(ix);

        assert_eq!(
            xs,
            vec![
                Transition::RemoveSnapshot.into(),
                Transition::MountSnapshot.into(),
            ]
            .into_iter()
            .collect()
        );
    }

    #[test]
    fn get_snapshot_remove_transitions() {
        let graph = build_graph();

        let ix = graph.get_state_node(snapshot::State::Removed).unwrap();

        let xs = graph.get_available_transitions(ix);

        assert_eq!(xs, vec![].into_iter().collect());
    }

    #[test]
    fn get_snapshot_mount_remove_transition() {
        let graph = build_graph();

        let xs = graph
            .get_transition_path(snapshot::State::Mounted, Transition::RemoveSnapshot)
            .unwrap();

        assert_eq!(xs, vec![Transition::RemoveSnapshot.into()]);
    }

    #[test]
    fn get_snapshot_mount_unmount_transition() {
        let graph = build_graph();

        let xs = graph
            .get_transition_path(snapshot::State::Mounted, Transition::UnmountSnapshot)
            .unwrap();

        assert_eq!(xs, vec![Transition::UnmountSnapshot.into()]);
    }

    #[test]
    fn show_dotviz() {
        let graph = build_graph();

        let dot = Dot::with_config(&graph, &[]);

        eprintln!("graph {:?}", dot);
    }
}
