// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use warp::Filter as _;

fn main() {
    env_logger::builder().default_format_timestamp(false).init();

    let routes = warp::path("mailbox")
        .and(warp::header::<String>("mailbox-address"))
        .and(iml_mailbox::line_stream())
        .map(|_, _| warp::reply())
        .with(warp::log("mailbox"));

    let addr = iml_manager_env::get_mailbox_addr();

    log::info!("Starting on {:?}", addr);

    warp::serve(routes).run(addr);
}
