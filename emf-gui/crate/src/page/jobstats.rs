// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::Model;
use seed::{prelude::*, *};

#[derive(Clone, Debug)]
pub enum Msg {}

pub fn view(_model: &Model) -> impl View<Msg> {
    div!["welcome to jobstats"]
}
