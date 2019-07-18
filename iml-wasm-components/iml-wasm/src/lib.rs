// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use cfg_if::cfg_if;

pub mod deferred_action_dropdown;
pub mod hsm_dropdown;
pub mod multi_action_dropdown;

pub use iml_fs::{fs_detail_page, fs_page};
pub use iml_stratagem;

cfg_if! {
    if #[cfg(feature = "console_log")] {
        fn init_log() {
            use log::Level;

            if let Err(e) = console_log::init_with_level(Level::Trace) {
                log::info!("Error initializing logger (it may have already been initialized): {:?}", e)
            }
        }
    } else {
        fn init_log() {}
    }
}
