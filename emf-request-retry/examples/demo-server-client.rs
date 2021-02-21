// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use emf_request_retry::policy::exponential_backoff_policy_builder;
use emf_request_retry::{retry_future, retry_future_gen, RetryAction};
use once_cell::sync::Lazy;
use reqwest::{Client, Response, Url};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fmt::Debug;
use std::io;
use std::net::SocketAddr;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::time::Duration;
use tokio::sync::mpsc::unbounded_channel;
use tokio::sync::Mutex;
use tokio::time::sleep;
use warp::http::StatusCode;
use warp::Filter;

#[derive(Serialize, Deserialize, Clone, Debug, Eq, PartialEq, Hash)]
struct ClientId(u32);

static GLOBAL_SERVER_STATE: Lazy<Mutex<HashMap<ClientId, AtomicUsize>>> = Lazy::new(|| {
    let mut hm = HashMap::new();
    // we know there are 3 clients only
    hm.insert(ClientId(1), AtomicUsize::new(0));
    hm.insert(ClientId(2), AtomicUsize::new(0));
    hm.insert(ClientId(3), AtomicUsize::new(0));
    Mutex::new(hm)
});

/// Messages from the server to clients during HTTP request.
#[derive(Serialize, Deserialize, Debug)]
struct Hello {
    client: ClientId,
    counter: Option<usize>,
}

/// Messages from main to clients without relation to HTTP requests.
#[derive(Clone, Debug)]
struct Fire;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let addr: SocketAddr = "127.0.0.1:8080".parse().unwrap();
    let (tx, mut rx) = unbounded_channel::<Fire>();

    // run server
    tokio::spawn(async move { server(&addr).await });

    // run 3 clients
    tokio::spawn(async move {
        let result = client_1(&addr).await;
        println!("client 1 received {:?}", result);
    });
    tokio::spawn(async move {
        let result = client_2(&addr).await;
        println!("client 2 received {:?}", result);
    });
    tokio::spawn(async move {
        while let Some(x) = rx.recv().await {
            let policy = exponential_backoff_policy_builder().build().unwrap();

            let r = retry_future(|_| http_call(&addr, 3), policy).await;
            println!("client 3 received {:?}", r);
            if let Err(e) = r {
                println!("Could not send result {:?}. Error {:?}", x, e);
            }
        }
        println!("channel has been dropped, end of transmission");
    });

    // Let's start the client with exponential backoff
    tx.send(Fire)?;

    println!("Wait for 20 seconds");
    for _ in 0..20u8 {
        {
            let hm = GLOBAL_SERVER_STATE.lock().await;
            println!("Server state: {:?}", hm);
        }
        sleep(Duration::from_secs(1)).await;
    }
    println!("End of waiting, shutting down");

    Ok(())
}

async fn server(addr: &SocketAddr) {
    let routes = warp::post().and(warp::body::json()).and_then(server_reply);
    warp::serve(routes).run(*addr).await;
}

async fn client_1(addr: &SocketAddr) -> Result<String, reqwest::Error> {
    let policy_1 = |k: u32, e| match k {
        0 => RetryAction::RetryNow,
        k if k < 3 => RetryAction::WaitFor(Duration::from_secs((2 * k) as u64)),
        _ => RetryAction::ReturnError(e),
    };
    retry_future(|_| http_call(addr, 1), policy_1).await
}

async fn client_2(addr: &SocketAddr) -> Result<String, reqwest::Error> {
    fn policy_2<E: Debug>(k: u32, _e: E) -> RetryAction<E> {
        if k == 0 {
            RetryAction::RetryNow
        } else {
            RetryAction::WaitFor(Duration::from_secs(5))
        }
    }
    retry_future_gen(|_| http_call(addr, 2), policy_2).await
}

async fn server_reply(mut hello: Hello) -> Result<Box<dyn warp::Reply>, warp::Rejection> {
    let count = {
        let hm = GLOBAL_SERVER_STATE.lock().await;
        let counter = hm.get(&hello.client).expect("Impossible server state");
        counter.fetch_add(1, Ordering::SeqCst) + 1
    };
    match hello.client {
        ClientId(1) | ClientId(2) => {
            // dispatch client 1
            if count % 5 == 0 {
                hello.counter = Some(count);
                Ok(Box::new(warp::reply::json(&hello)) as Box<dyn warp::Reply>)
            } else {
                Ok(Box::new(StatusCode::INTERNAL_SERVER_ERROR) as Box<dyn warp::Reply>)
            }
        }
        ClientId(3) => {
            // dispatch client 3
            if count % 7 == 0 {
                hello.counter = Some(count);
                Ok(Box::new(warp::reply::json(&hello)) as Box<dyn warp::Reply>)
            } else {
                Ok(Box::new(StatusCode::INTERNAL_SERVER_ERROR) as Box<dyn warp::Reply>)
            }
        }
        _ => unreachable!("Impossible client number"),
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
