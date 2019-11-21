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
    use futures::{future::Either, Stream};
    use std::{
        env, io,
        os::unix::{io::FromRawFd, net::UnixListener as NetUnixListener},
    };
    use tokio::{
        io::{AsyncRead, AsyncWrite},
        net::{unix::UnixListener, TcpListener},
        reactor::Handle,
    };

    pub trait Socket: AsyncRead + AsyncWrite + Send + 'static {}
    impl<T: AsyncRead + AsyncWrite + Send + 'static> Socket for T {}

    /// Given an environment variable that resolves to a port,
    /// Return a stream containing `TcpStream`s that have been erased to
    /// `AsyncRead` + `AsyncWrite` traits. This is useful when you won't know which stream
    /// to choose at runtime
    pub fn get_tcp_stream(
        port: String,
    ) -> Result<impl Stream<Item = Box<dyn Socket>, Error = io::Error>, io::Error> {
        let addr = format!("127.0.0.1:{}", port)
            .parse()
            .expect("Couldn't parse socket address.");

        tracing::debug!("Listening over tcp port {}", port);

        let listener = TcpListener::bind(&addr)?;
        let s = listener
            .incoming()
            .map(|x| -> Box<dyn Socket> { Box::new(x) });

        Ok(s)
    }

    /// Returns a stream containing `UnixStream`s that have been erased to
    /// `AsyncRead` + `AsyncWrite` traits. This is useful when you won't know which stream
    /// to choose at runtime
    pub fn get_unix_stream(
    ) -> Result<impl Stream<Item = Box<dyn Socket>, Error = io::Error>, io::Error> {
        let addr = unsafe { NetUnixListener::from_raw_fd(3) };

        tracing::debug!("Listening over unix domain socket");

        let s = UnixListener::from_std(addr, &Handle::default())?
            .incoming()
            .map(|socket| -> Box<dyn Socket> { Box::new(socket) });

        Ok(s)
    }

    /// Given an environment variable that resolves to a port,
    /// Return a stream containing items that have been erased to
    /// `AsyncRead` + `AsyncWrite` traits. This is useful when you won't know which stream
    /// to choose at runtime.
    ///
    /// If the `port_var` resolves to a port, `TcpStream` will be used internally.
    /// Otherwise a `UnixStream` will be used.
    pub fn get_tcp_or_unix_listener(
        port_var: &str,
    ) -> Result<impl Stream<Item = Box<dyn Socket>, Error = io::Error>, io::Error> {
        let s = match env::var(port_var) {
            Ok(port) => Either::A(get_tcp_stream(port)?),
            Err(_) => Either::B(get_unix_stream()?),
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
