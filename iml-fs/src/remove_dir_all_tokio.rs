use futures::{
    Async,
    Poll as FeaturePoll,
};
use std::{
    fs,
    future::Future,
    io,
    path::Path,
    pin::Pin,
    task::{Context, Poll},
};
use tokio_threadpool::blocking;


/// tokio-fs.remove_dir_all

/// Removes a directory at this path, after removing all its contents. Use carefully!
///
/// This is an async version of [`std::fs::remove_dir_all`][std]
///
/// [std]: https://doc.rust-lang.org/std/fs/fn.remove_dir_all.html
pub fn remove_dir_all<P: AsRef<Path>>(path: P) -> RemoveDirAllFuture<P> {
    RemoveDirAllFuture::new(path)
}

/// Future returned by `remove_dir_all`.
#[derive(Debug)]
#[must_use = "futures do nothing unless you `.await` or poll them"]
pub struct RemoveDirAllFuture<P>
where
    P: AsRef<Path>,
{
    path: P,
}

impl<P> RemoveDirAllFuture<P>
where
    P: AsRef<Path>,
{
    fn new(path: P) -> RemoveDirAllFuture<P> {
        RemoveDirAllFuture { path }
    }
}

impl<P> Future for RemoveDirAllFuture<P>
where
    P: AsRef<Path>,
{
    type Output = io::Result<()>;

    fn poll(self: Pin<&mut Self>, _cx: &mut Context<'_>) -> Poll<Self::Output> {
        blocking_io(|| fs::remove_dir_all(&self.path))
    }
}

/// tokio-fs.lib
fn blocking_io<F, T>(f: F) -> Poll<io::Result<T>>
where
    F: FnOnce() -> io::Result<T>,
{
    match tokio_threadpool::blocking(f) {
        FeaturePoll::Ok(Async::Ready(v)) => Poll::Ready(v),
        FeaturePoll::Ok(Async::NotReady) => Poll::Pending,
        FeaturePoll::Err(_) => Poll::Ready(io::Result::Err(blocking_err())),
    }
}

fn blocking_err() -> io::Error {
    io::Error::new(
        io::ErrorKind::Other,
        "`blocking` annotated I/O must be called \
         from the context of the Tokio runtime.",
    )
}
