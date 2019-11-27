// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub mod action_plugin;
pub mod check_ha;
pub mod check_kernel;
pub mod check_stonith;
pub mod ostpool;
pub mod package_installed;
pub mod stratagem;
pub use action_plugin::create_registry;
