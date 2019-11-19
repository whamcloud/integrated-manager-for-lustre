// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use std::io;
use std::collections::HashMap;
use reqwest::{Client, Response, Url};
use iml_request_retry::{RetryAction, retry_future, retry_future_gen};
use std::time::Duration;
use std::fmt::Debug;

#[tokio::main]
async fn main() -> Result<(), reqwest::Error> {

    let mut policy_1 = |k: u32, e| {
        match k {
            0 => RetryAction::RetryNow,
            k if k < 3 => RetryAction::WaitFor(Duration::from_secs((2 * k) as u64)),
            _ => RetryAction::ReturnError(e),
        }
    };

    let r = retry_future(|| http_call(42), &mut policy_1).await;
    println!("r = {:?}", r);

    fn policy_2<E: Debug>(k: u32, _e: E) -> RetryAction<E> {
        if k == 0 { RetryAction::RetryNow }
        else { RetryAction::WaitFor(Duration::from_secs(5)) }
    }

    let r = retry_future_gen(|| http_call(42), policy_2).await;
    println!("r = {:?}", r);
    Ok(())
}


pub async fn http_call(_n: u32) -> reqwest::Result<String> {
    let uri = Url::parse(&"http://127.0.0.1:5000/fail5").unwrap();

    let mut map = HashMap::new();
    map.insert("hello", true);

    // GET request with body
    let client: Client = reqwest::Client::new();
    let resp: Response = client
        .get(uri)
        .json(&map)
        .send()
        .await?;

    match resp.error_for_status() {
        Ok(resp) => {
            let resp_body = resp
                .text()
                .await?
                .to_string();
            Ok(resp_body)
        }
        Err(err) => Err(err)
    }
}

#[derive(Debug)]
pub enum MyError {
    IoError(io::Error),
    ReqwestError(reqwest::Error),
    ParseError(url::ParseError),
    AppError,
}

//pub type Result<T> = ::std::result::Result<T, MyError>;


impl From<io::Error> for MyError {
    fn from(err: io::Error) -> MyError {
        MyError::IoError(err)
    }
}

impl From<reqwest::Error> for MyError {
    fn from(err: reqwest::Error) -> MyError {
        MyError::ReqwestError(err)
    }
}

impl From<url::ParseError> for MyError {
    fn from(err: url::ParseError) -> MyError {
        MyError::ParseError(err)
    }
}
