// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use seed::prelude::*;

#[derive(Clone, Debug)]
pub enum Msg {}

pub struct Model {
    pub id: i32,
}

pub fn view(_model: &Model) -> impl View<Msg> {
    seed::empty()
}
