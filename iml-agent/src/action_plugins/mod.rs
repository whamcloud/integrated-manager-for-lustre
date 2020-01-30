// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub mod action_plugin;
pub mod check_ha;
pub mod check_kernel;
pub mod check_stonith;
pub mod kernel_module;
pub mod lamigo;
pub mod lpurge;
pub mod ltuer;
pub mod lustre;
pub mod ntp;
pub mod ostpool;
pub mod package;
pub mod postoffice;
pub mod stratagem;
pub use action_plugin::create_registry;
