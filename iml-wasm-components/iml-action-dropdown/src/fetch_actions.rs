// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    api_transforms::{composite_ids_to_query_string, group_actions_by_label, sort_actions},
    sleep, AvailableActionsApiData, Model, Msg, RecordMap,
};
use futures::{
    future::{loop_fn, Either, Loop},
    Future, Stream,
};
use seed::{prelude::JsValue, Method, Request};

/// Fetches the actions for the given composite ids
pub fn get_actions(state: seed::App<Msg, Model>) -> impl Future<Item = (), Error = JsValue> {
    let (start_tx, start_rx) = futures::sync::mpsc::unbounded::<RecordMap>();
    let (stop_tx, stop_rx) = futures::sync::mpsc::unbounded::<()>();

    state.add_message_listener(move |msg| match msg {
        Msg::Destroy => {
            stop_tx.unbounded_send(()).expect("Error stopping fetch");
        }
        Msg::StartFetch(records) => start_tx
            .unbounded_send(records.clone())
            .expect("Error starting fetch"),
        _ => (),
    });

    start_rx
        .into_future()
        .map_err(|_| unreachable!())
        .map(|(x, _)| x.unwrap())
        .and_then(move |records| {
            loop_fn(stop_rx.into_future(), move |rx| {
                let records2 = records.clone();
                let state2 = state.clone();

                let req = Request::new(&format!(
                    "/api/action/?limit=0&{}",
                    composite_ids_to_query_string(&records)
                ))
                .method(Method::Get)
                .fetch_json()
                .map(move |AvailableActionsApiData { objects, .. }| {
                    group_actions_by_label(objects, records2)
                        .into_iter()
                        .map(|(k, xs)| (k, sort_actions(xs)))
                        .collect()
                })
                .map(move |actions| {
                    state2.update(Msg::AvailableActions(actions));
                })
                .and_then(|_| sleep::Sleep::new(10000));

                req.select2(rx)
                    .map(|r| match r {
                        Either::A((_, rx)) => Loop::Continue(rx),
                        Either::B((_, req)) => {
                            drop(req);
                            Loop::Break(())
                        }
                    })
                    .map_err(|e| match e {
                        Either::A((e, _)) => e,
                        Either::B((_, _)) => unreachable!(),
                    })
            })
        })
}
