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
    };
        net::{TcpListener, UnixListener},

    pub trait Socket: AsyncRead + AsyncWrite + Send + 'static + Unpin {}
    impl<T: AsyncRead + AsyncWrite + Send + 'static + Unpin> Socket for T {}
    pub async fn get_tcp_stream(

    /// Given an environment variable that resolves to a port,
    /// Return a stream containing `TcpStream`s that have been erased to
    /// `AsyncRead` + `AsyncWrite` traits. This is useful when you won't know which stream
    /// to choose at runtime
        port: String,
    ) -> Result<impl Stream<Item = Result<Pin<Box<dyn Socket>>, io::Error>>, io::Error> {
        let addr = format!("127.0.0.1:{}", port);

        tracing::debug!("Listening over tcp port {}", port);

        let s = TcpListener::bind(&addr)
            .await?
            .incoming()
            .map_ok(|x| -> Pin<Box<dyn Socket>> { Box::pin(x) });

    }
        Ok(s)

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
            Ok(port) => Either::Left(get_tcp_stream(port).await?),
            Err(_) => Either::Right(get_unix_stream()?),

        };
        Ok(s)
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
