// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use emf_request_retry::{retry_future, retry_future_gen, RetryAction};
use reqwest::{Client, Response, Url};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fmt::Debug;
use std::io;
use std::net::SocketAddr;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::time::Duration;
use tokio::time::delay_for;
use warp::http::StatusCode;
use warp::Filter;

static GLOBAL_SERVER_COUNTER: AtomicUsize = AtomicUsize::new(0);

/// A serialized message to report in JSON format.
#[derive(Serialize, Deserialize, Debug)]
struct Hello {
    client: u32,
    counter: Option<usize>,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let addr: SocketAddr = "127.0.0.1:8080".parse().unwrap();

    // run server
    tokio::spawn(async move { server(&addr).await });

    // run 2 clients
    tokio::spawn(async move {
        let result = retry_client_obj(&addr, 1).await;
        println!("retry_client_obj received {:?}", result);
    });
    tokio::spawn(async move {
        let result = retry_client_fun(&addr, 2).await;
        println!("retry_client_fun received {:?}", result);
    });

    println!("Sleep for 30 seconds");
    delay_for(Duration::from_secs(30)).await;
    println!("End of sleep, shutting down");

    Ok(())
}

async fn server(addr: &SocketAddr) {
    let routes = warp::post().and(warp::body::json()).and_then(server_reply);
    warp::serve(routes).run(*addr).await;
}

async fn retry_client_obj(addr: &SocketAddr, client_id: u32) -> Result<String, reqwest::Error> {
    let policy_1 = |k: u32, e| match k {
        0 => RetryAction::RetryNow,
        k if k < 3 => RetryAction::WaitFor(Duration::from_secs((2 * k) as u64)),
        _ => RetryAction::ReturnError(e),
    };

    retry_future(|_| http_call(addr, client_id), policy_1).await
}

async fn retry_client_fun(addr: &SocketAddr, client_id: u32) -> Result<String, reqwest::Error> {
    fn policy_2<E: Debug>(k: u32, _e: E) -> RetryAction<E> {
        if k == 0 {
            RetryAction::RetryNow
        } else {
            RetryAction::WaitFor(Duration::from_secs(5))
        }
    }
    retry_future_gen(|_| http_call(addr, client_id), policy_2).await
}

async fn server_reply(mut hello: Hello) -> Result<Box<dyn warp::Reply>, warp::Rejection> {
    GLOBAL_SERVER_COUNTER.fetch_add(1, Ordering::SeqCst);
    let counter = GLOBAL_SERVER_COUNTER.load(Ordering::SeqCst);
    if counter % 5 == 0 {
        hello.counter = Some(counter);
        println!(
            "Incoming request from client={}, counter={}",
            hello.client, counter
        );
        Ok(Box::new(warp::reply::json(&hello)) as Box<dyn warp::Reply>)
    } else {
        println!(
            "Incoming request from client={}, counter={}, server is going to fail",
            hello.client, counter
        );
        Ok(Box::new(StatusCode::INTERNAL_SERVER_ERROR) as Box<dyn warp::Reply>)
    }
}

pub async fn http_call(addr: &SocketAddr, id: u32) -> reqwest::Result<String> {
    let uri = Url::parse(&format!("http://{}", addr)).unwrap();

    let mut map = HashMap::new();
    map.insert("client", id);

    // GET request with body
    let client: Client = reqwest::Client::new();
    let resp: Response = client.post(uri).json(&map).send().await?;

    Ok(resp.error_for_status()?.text().await?)
}

#[derive(Debug)]
pub enum MyError {
    IoError(io::Error),
    ReqwestError(reqwest::Error),
    ParseError(url::ParseError),
    AppError,
}

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
