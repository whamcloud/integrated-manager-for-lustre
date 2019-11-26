// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub trait Flatten<T> {
    fn flatten(self) -> Option<T>;
}

/// Implement flatten for the `Option` type.
/// See https://doc.rust-lang.org/std/option/enum.Option.html#method.flatten
/// for more information.
impl<T> Flatten<T> for Option<Option<T>> {
    fn flatten(self) -> Option<T> {
        self.unwrap_or(None)
    }
}

pub trait Pick<A, B> {
    fn fst(self) -> A;
    fn snd(self) -> B;
}

impl<A, B> Pick<A, B> for (A, B) {
    fn fst(self) -> A {
        self.0
    }
    fn snd(self) -> B {
        self.1
    }
}

impl<A, B, C> Pick<A, B> for (A, B, C) {
    fn fst(self) -> A {
        self.0
    }
    fn snd(self) -> B {
        self.1
    }
}

impl<A, B, C, D> Pick<A, B> for (A, B, C, D) {
    fn fst(self) -> A {
        self.0
    }
    fn snd(self) -> B {
        self.1
    }
}

impl<A, B, C, D, E> Pick<A, B> for (A, B, C, D, E) {
    fn fst(self) -> A {
        self.0
    }
    fn snd(self) -> B {
        self.1
    }
}

pub mod tokio_utils {
    use futures::{future::Either, Stream, TryStreamExt};
    use std::{
        convert::TryFrom,
        env, io,
        os::unix::{io::FromRawFd, net::UnixListener as NetUnixListener},
        pin::Pin,
    };
    use tokio::{
        io::{AsyncRead, AsyncWrite},
        net::{TcpListener, UnixListener},
    };

    pub trait Socket: AsyncRead + AsyncWrite + Send + 'static + Unpin {}
    impl<T: AsyncRead + AsyncWrite + Send + 'static + Unpin> Socket for T {}

    /// Given an environment variable that resolves to a port,
    /// Return a stream containing `TcpStream`s that have been erased to
    /// `AsyncRead` + `AsyncWrite` traits. This is useful when you won't know which stream
    /// to choose at runtime
    pub async fn get_tcp_stream(
        port: &str,
    ) -> Result<impl Stream<Item = Result<Pin<Box<dyn Socket>>, io::Error>>, io::Error> {
        let host = env::var("PROXY_HOST").or::<String>(Ok("127.0.0.1".into())).expect("Couldn't parse host.");
        let addr = format!("{}:{}", host, port);

        tracing::debug!("Listening over tcp port {}", port);

        let s = TcpListener::bind(&addr)
            .await?
            .incoming()
            .map_ok(|x| -> Pin<Box<dyn Socket>> { Box::pin(x) });

        Ok(s)
    }

    /// Returns a stream containing `UnixStream`s that have been erased to
    /// `AsyncRead` + `AsyncWrite` traits. This is useful when you won't know which stream
    /// to choose at runtime
    pub fn get_unix_stream(
    ) -> Result<impl Stream<Item = Result<Pin<Box<dyn Socket>>, io::Error>>, io::Error> {
        let addr = unsafe { NetUnixListener::from_raw_fd(3) };

        tracing::debug!("Listening over unix domain socket");

        let s = UnixListener::try_from(addr)?
            .incoming()
            .map_ok(|x| -> Pin<Box<dyn Socket>> { Box::pin(x) });

        Ok(s)
    }

    /// Given an environment variable that resolves to a port,
    /// Return a stream containing items that have been erased to
    /// `AsyncRead` + `AsyncWrite` traits. This is useful when you won't know which stream
    /// to choose at runtime.
    ///
    /// If the `port_var` resolves to a port, `TcpStream` will be used internally.
    /// Otherwise a `UnixStream` will be used.
    pub async fn get_tcp_or_unix_listener(
        port_var: &str,
    ) -> Result<impl Stream<Item = Result<Pin<Box<dyn Socket>>, io::Error>>, io::Error> {
        let s = match env::var(port_var) {
            Ok(port) => Either::Left(get_tcp_stream(&port).await?),
            Err(_) => Either::Right(get_unix_stream()?),
        };

        Ok(s)
    }
}

pub mod action_plugins {
    use futures::{Future, FutureExt};
    use iml_wire_types::{ActionName, ToJsonValue};
    use std::{collections::HashMap, fmt::Display, pin::Pin};

    type BoxedFuture =
        Pin<Box<dyn Future<Output = Result<serde_json::value::Value, String>> + Send>>;

    /// Wrapper for an action plugin to be used as a trait object for different actions.
    /// The incoming `Value` is the data to be sent to the plugin. It will be deserialized to the parameter
    /// type needed by the specific plugin.
    type Callback = Box<dyn Fn(serde_json::value::Value) -> BoxedFuture + Send + Sync>;

    /// Runs a given plugin. First deserializes data to the required type,
    /// then runs the plugin and serializes the result.
    async fn run_plugin<T, R, E: Display, Fut>(
        v: serde_json::value::Value,
        f: fn(T) -> Fut,
    ) -> Result<serde_json::value::Value, String>
    where
        T: serde::de::DeserializeOwned + Send,
        R: serde::Serialize + Send,
        Fut: Future<Output = Result<R, E>> + Send,
    {
        let x = serde_json::from_value(v).map_err(|e| format!("{}", e))?;

        let x = f(x).await.map_err(|e| format!("{}", e))?;

        x.to_json_value()
    }

    fn mk_callback<Fut, T, R, E>(f: fn(T) -> Fut) -> Callback
    where
        Fut: Future<Output = Result<R, E>> + Send + 'static,
        T: serde::de::DeserializeOwned + Send + 'static,
        R: serde::Serialize + Send + 'static,
        E: Display + 'static,
    {
        Box::new(move |v| run_plugin(v, f).boxed())
    }

    /// The registry of available plugins.
    /// This is modeled internally as a `HashMap` so plugins can be supplied
    /// in different ways at runtime.
    pub struct Actions(HashMap<ActionName, Callback>);

    impl Actions {
        pub fn new() -> Self {
            Actions(HashMap::new())
        }
        pub fn add_plugin<Fut, T, R, E>(mut self, s: impl Into<ActionName>, f: fn(T) -> Fut) -> Self
        where
            Fut: Future<Output = Result<R, E>> + Send + 'static,
            T: serde::de::DeserializeOwned + Send + 'static,
            R: serde::Serialize + Send + 'static,
            E: Display + 'static,
        {
            self.0.insert(s.into(), mk_callback(f));

            self
        }
        pub fn keys(&self) -> impl Iterator<Item = &ActionName> {
            self.0.keys()
        }
        pub fn get(&self, name: &ActionName) -> Option<&Callback> {
            self.0.get(name)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_option_of_some() {
        let x = Some(Some(7));
        assert_eq!(x.flatten(), Some(7));
    }

    #[test]
    fn test_option_of_none() {
        let x: Option<Option<i32>> = Some(None);
        assert_eq!(x.flatten(), None);
    }

    #[test]
    fn test_option_of_option_of_some() {
        let x = Some(Some(Some(7)));
        assert_eq!(x.flatten().flatten(), Some(7));
    }

    #[test]
    fn test_option_of_option_of_none() {
        let x: Option<Option<Option<u32>>> = Some(Some(None));
        assert_eq!(x.flatten().flatten(), None);
    }
}
