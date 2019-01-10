// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub mod locks;
pub mod request;
pub mod users;

/// Message variants.
#[derive(Debug)]
pub enum Message {
    UserId(usize),
    Data(String),
}
