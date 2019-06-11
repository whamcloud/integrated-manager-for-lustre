// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    model::{composite_ids_to_query_string, RecordMap},
    update::Msg,
};
use futures::Future;
use seed::Request;

/// Performs a fetch to get the current available actions based on given
/// composite ids.
pub fn fetch_actions(
    records: &RecordMap,
) -> (
    impl Future<Item = Msg, Error = Msg>,
    Option<seed::fetch::RequestController>,
) {
    let mut request_controller = None;

    let fut = Request::new(format!(
        "/api/action/?limit=0&{}",
        composite_ids_to_query_string(&records)
    ))
    .controller(|controller| request_controller = Some(controller))
    .fetch_json(Msg::ActionsFetched);

    (fut, request_controller)
}
