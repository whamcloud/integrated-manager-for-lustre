// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::lazy;
use iml_rabbit::connect_to_rabbit;
use iml_service_queue::service_queue::{consume_service_queue, data_only, into_deserialized};
use iml_wire_types::Fqdn;
use tokio::prelude::*;

fn main() {
    env_logger::init();

    tokio::run(lazy(move || {
        connect_to_rabbit()
            .map(|client| consume_service_queue(client, "rust_agent_stratagem_rx"))
            .flatten_stream()
            .filter_map(data_only)
            .and_then(into_deserialized)
            .for_each(|m: (Fqdn, String)| {
                log::info!("Got some stratagem data: {:?}", m.1);

                Ok(())
            })
            .map_err(|e| {
                log::error!("An error occured: {:?}", e);
            })
    }));
}
