// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::components::sfa_overview::{build_expansion, enclosures::ss9012, Expansion};
use emf_wire_types::warp_drive::ArcCache;
use seed::prelude::*;
use std::sync::Arc;

#[derive(Clone, Debug)]
pub enum Msg {}

pub struct Model {
    pub id: i32,
}

pub fn view(cache: &ArcCache, model: &Model) -> impl View<Msg> {
    let enc = cache.sfa_enclosure.get(&model.id).unwrap();

    let expansion = build_expansion(cache, Arc::clone(&enc)).unwrap();

    match expansion {
        Expansion::SS9012(x) => ss9012::view(&x),
    }
}
