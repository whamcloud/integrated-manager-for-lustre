// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::{Future, FutureExt};
use petgraph::graph::DiGraph;
use std::{ io, pin::Pin};

pub enum LnetStates {
    Unconfigured,
    Unloaded,
    Down,
    Up,
}

impl Default for LnetStates {
    fn default() -> Self {
        Self::Unconfigured
    }
}

impl LnetStates {
    fn step(self, next: &Self) {
        match (self, next) {
            (Self::Unconfigured, Self::Unloaded) => {}
            (Self::Unloaded, Self::Down) => {}
            (Self::Down, Self::Up) => {}
            (Self::Up, Self::Down) => {}
            (Self::Down, Self::Unloaded) => {}
            (Self::Unloaded, Self::Unconfigured) => {}
            _ => {}
        };
    }
}

async fn configure() -> Result<(), io::Error> {
    Ok(())
}

async fn load() -> Result<(), io::Error> {
    Ok(())
}

async fn start() -> Result<(), io::Error> {
    Ok(())
}

async fn stop() -> Result<(), io::Error> {
    Ok(())
}

async fn unload() -> Result<(), io::Error> {
    Ok(())
}

async fn unconfigure() -> Result<(), io::Error> {
    Ok(())
}

type BoxedFuture = Pin<Box<dyn Future<Output = Result<(), io::Error>> + Send>>;

type Transition = Box<dyn Fn() -> BoxedFuture + Send + Sync>;

fn mk_transition<Fut>(f: fn() -> Fut) -> Transition
where
    Fut: Future<Output = Result<(), io::Error>> + Send + 'static,
{
    Box::new(move || f().boxed())
}

fn build_graph() -> DiGraph::<LnetStates, Transition> {
    let mut deps = DiGraph::<LnetStates, Transition>::new();

    let unconfigured = deps.add_node(LnetStates::Unconfigured);
    let unloaded = deps.add_node(LnetStates::Unloaded);
    let down = deps.add_node(LnetStates::Down);
    let up = deps.add_node(LnetStates::Up);

    deps.add_edge(unconfigured, unloaded, mk_transition(configure));
    deps.add_edge(unloaded, down, mk_transition(load));
    deps.add_edge(down, up, mk_transition(start));
    deps.add_edge(up, down, mk_transition(stop));
    deps.add_edge(down, unloaded, mk_transition(unload));
    deps.add_edge(unloaded, unconfigured, mk_transition(unconfigure));

    deps

}
