// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub mod env;
pub mod locks;
pub mod rabbit;
pub mod request;
pub mod users;

use futures::Future;
use lapin_futures::{channel::Channel, client::Client};
use tokio::net::TcpStream;

pub type TcpClient = Client<TcpStream>;
pub type TcpChannel = Channel<TcpStream>;

pub trait TcpChannelFuture: Future<Item = TcpChannel, Error = failure::Error> {}
impl<T: Future<Item = TcpChannel, Error = failure::Error>> TcpChannelFuture for T {}

/// Message variants.
#[derive(Debug)]
pub enum Message {
    UserId(usize),
    Data(String),
}
