// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

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
    use futures::{stream::BoxStream, StreamExt, TryStreamExt};
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

    pub trait Socket: AsyncRead + AsyncWrite + Send {}
    impl<T: AsyncRead + AsyncWrite + Send> Socket for T {}

    pub trait Incoming: Send {
        fn incoming(&'_ mut self) -> BoxStream<'_, Result<Pin<Box<dyn Socket>>, io::Error>>;
    }

    struct TcpIncoming(TcpListener);

    impl Incoming for TcpIncoming {
        fn incoming(&'_ mut self) -> BoxStream<'_, Result<Pin<Box<dyn Socket>>, io::Error>> {
            self.0
                .incoming()
                .map_ok(|x| -> Pin<Box<dyn Socket>> { Box::pin(x) })
                .boxed()
        }
    }

    struct UnixIncoming(UnixListener);

    impl Incoming for UnixIncoming {
        fn incoming(&'_ mut self) -> BoxStream<'_, Result<Pin<Box<dyn Socket>>, io::Error>> {
            self.0
                .incoming()
                .map_ok(|x| -> Pin<Box<dyn Socket>> { Box::pin(x) })
                .boxed()
        }
    }

    /// Given an environment variable that resolves to a port,
    /// Return a stream containing `TcpStream`s that have been erased to
    /// `AsyncRead` + `AsyncWrite` traits. This is useful when you won't know which stream
    /// to choose at runtime
    async fn get_tcp_stream(port: &str) -> Result<Box<dyn Incoming>, io::Error> {
        let host = env::var("PROXY_HOST")
            .or_else::<String, _>(|_| Ok("127.0.0.1".into()))
            .expect("Couldn't parse host.");
        let addr = format!("{}:{}", host, port);

        tracing::debug!("Listening over tcp port {}", port);

        Ok(Box::new(TcpIncoming(TcpListener::bind(&addr).await?)))
    }

    /// Returns a stream containing `UnixStream`s that have been erased to
    /// `AsyncRead` + `AsyncWrite` traits. This is useful when you won't know which stream
    /// to choose at runtime
    fn get_unix_stream() -> Result<Box<dyn Incoming>, io::Error> {
        let addr = unsafe { NetUnixListener::from_raw_fd(3) };

        tracing::debug!("Listening over unix domain socket");

        Ok(Box::new(UnixIncoming(UnixListener::try_from(addr)?)))
    }

    /// Given an environment variable that resolves to a port,
    /// Return a stream containing items that have been erased to
    /// `AsyncRead` + `AsyncWrite` traits. This is useful when you won't know which stream
    /// to choose at runtime.
    ///
    /// If the `port_var` resolves to a port, `TcpStream` will be used internally.
    /// Otherwise a `UnixStream` will be used.
    pub async fn get_tcp_or_unix_listener(port_var: &str) -> Result<Box<dyn Incoming>, io::Error> {
        match env::var(port_var) {
            Ok(port) => get_tcp_stream(&port).await,
            Err(_) => get_unix_stream(),
        }
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

    impl Default for Actions {
        fn default() -> Self {
            Actions(HashMap::new())
        }
    }

    impl Actions {
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
