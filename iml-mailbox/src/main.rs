// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use warp::Filter as _;

fn main() {
    env_logger::builder().default_format_timestamp(false).init();

    let log = warp::log("iml_agent_comms::api");

    let routes = warp::path("mailbox")
        .and(iml_mailbox::line_stream())
        .map(|_| warp::reply())
        .with(log);

    // let routes = warp::path("message").and(receiver.or(sender).with(log));

    // let addr = iml_manager_env::get_http_agent2_addr();

    // log::info!("Starting iml-agent-comms on {:?}", addr);

    // let (_, fut) = warp::serve(routes).bind_with_graceful_shutdown(addr, rx);
}
