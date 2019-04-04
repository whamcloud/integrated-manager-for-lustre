// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::lazy;
use iml_services::service_queue::consume_service_queue;
use iml_wire_types::PluginMessage;
use tokio::prelude::*;

fn main() {
    env_logger::init();

    tokio::run(lazy(move || {
        iml_rabbit::connect_to_rabbit()
            .and_then(move |client| {
                consume_service_queue(client.clone(), "agent_action_runner2_rx").for_each(
                    |m: PluginMessage| {
                        log::info!("Got some actiony data: {:?}", m);

                        match m {
                            PluginMessage::SessionCreate { .. } => {}
                            PluginMessage::SessionTerminate { .. } => {}
                            PluginMessage::Data { .. } => {}
                        };

                        Ok(())
                    },
                )
            })
            .map_err(|e| {
                log::error!("An error occured: {:?}", e);
            })
    }));
}
