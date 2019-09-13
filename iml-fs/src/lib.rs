// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

mod remove_dir_all;

pub use crate::remove_dir_all::{remove_dir_all, RemoveDirAllFuture};

use bytes::IntoBuf;
use futures::{future::poll_fn, stream, Future, Stream};
use std::{
    io::{self, Write},
    path::{Path, PathBuf},
};
use tempfile::NamedTempFile;
use tokio::codec::{BytesCodec, FramedRead, FramedWrite, LinesCodec};
use tokio_threadpool::blocking;

/// Given a `Stream` of items that implement `IntoBuf`, returns a stream
/// that reads line by line.
pub fn read_lines<S>(s: S) -> impl Stream<Item = String, Error = io::Error>
where
    S: Stream,
    S::Error: std::error::Error + Send + Sync + 'static,
    S::Item: IntoBuf,
{
    FramedRead::new(
        rw_stream_sink::RwStreamSink::new(s.map_err(|e| io::Error::new(io::ErrorKind::Other, e))),
        LinesCodec::new(),
    )
}

/// Given a path, attempts to do an async read to the end of the file.
///
/// # Arguments
///
/// * `p` - The `Path` to a file.
pub fn read_file_to_end<P>(p: P) -> impl Future<Item = Vec<u8>, Error = io::Error>
where
    P: AsRef<Path> + Send + 'static,
{
    tokio::fs::File::open(p)
        .from_err()
        .and_then(|file| tokio::io::read_to_end(file, vec![]).map(|(_, d)| d))
}

/// Given a path, streams the file till EOF
///
/// # Arguments
///
/// * `p` - The `Path` to a file.
pub fn stream_file<P>(p: P) -> impl Stream<Item = bytes::Bytes, Error = std::io::Error>
where
    P: AsRef<Path> + Send + 'static,
{
    tokio::fs::File::open(p)
        .map(|file| FramedRead::new(file, BytesCodec::new()))
        .flatten_stream()
        .map(bytes::BytesMut::freeze)
        .from_err()
}

/// Given a path, streams the file line by line till EOF
///
/// # Arguments
///
/// * `p` - The `Path` to a file.
pub fn stream_file_lines<P>(p: P) -> impl Stream<Item = String, Error = std::io::Error>
where
    P: AsRef<Path> + Send + 'static,
{
    tokio::fs::File::open(p)
        .map(|file| FramedRead::new(file, LinesCodec::new()))
        .flatten_stream()
        .from_err()
}

/// Given a directory of files,
/// stream each file line by line one at a time till EOF
///
/// # Arguments
///
/// * `p` - The `Path` to a directory.
pub fn stream_dir_lines<P>(p: P) -> impl Stream<Item = String, Error = std::io::Error>
where
    P: AsRef<Path> + Send + 'static,
{
    tokio::fs::read_dir(p)
        .flatten_stream()
        .map(|d| d.path())
        .map(stream_file_lines)
        .flatten()
}

/// Given a directory of files,
/// stream each file one at a time till EOF
///
/// # Arguments
///
/// * `p` - The `Path` to a directory.
pub fn stream_dir<P>(p: P) -> impl Stream<Item = bytes::Bytes, Error = std::io::Error>
where
    P: AsRef<Path> + Send + 'static,
{
    tokio::fs::read_dir(p)
        .flatten_stream()
        .map(|d| d.path())
        .map(stream_file)
        .flatten()
}

/// Given an iterator of directory of files,
/// stream each file one at a time till EOF
///
/// # Arguments
///
/// * `ps` - An `Iterator` of directory `Path`s.
pub fn stream_dirs<P>(
    ps: impl IntoIterator<Item = P>,
) -> impl Stream<Item = bytes::Bytes, Error = std::io::Error>
where
    P: AsRef<Path> + Send + 'static,
{
    stream::iter_ok::<_, std::io::Error>(ps)
        .map(stream_dir)
        .flatten()
}

/// Creates a temporary file and writes some bytes to it.
pub fn write_tempfile(contents: Vec<u8>) -> impl Future<Item = NamedTempFile, Error = io::Error> {
    poll_fn(move || {
        blocking(|| {
            let mut f = NamedTempFile::new()?;

            f.write_all(contents.as_ref())?;

            Ok(f)
        })
        .map_err(|_| panic!("the threadpool shut down"))
    })
    .and_then(|x| x)
}

/// Given a `PathBuf`, creates a new file that can have
/// arbitrary `Bytes` written to it.
pub fn file_write_bytes(
    path: PathBuf,
) -> impl Future<Item = FramedWrite<tokio::fs::File, BytesCodec>, Error = io::Error> {
    tokio::fs::File::create(path).map(|file| FramedWrite::new(file, BytesCodec::new()))
}

#[cfg(test)]
mod tests {
    use super::{stream_dir, stream_file, write_tempfile};
    use bytes::Bytes;
    use futures::{Future, Stream as _};
    use std::{fs::File, io, io::Write as _};
    use tempdir::TempDir;
    use tempfile::NamedTempFile;

    fn run<R: Send + 'static, E: Send + 'static>(
        fut: impl Future<Item = R, Error = E> + Send + 'static,
    ) -> Result<R, E> {
        tokio::runtime::Runtime::new().unwrap().block_on_all(fut)
    }

    #[test]
    fn test_write_tempfile() {
        let fut = write_tempfile(b"foobar".to_vec());

        let file = run(fut).unwrap();

        let s = std::fs::read_to_string(file.path()).unwrap();

        assert_eq!(s, "foobar");
    }

    #[test]
    fn test_stream_file() -> io::Result<()> {
        let mut f = NamedTempFile::new()?;

        f.write_all(b"some\nawesome\nfile")?;

        let path = f.path().to_path_buf();

        let fut = stream_file(path).collect();

        let result = run(fut)?;

        assert_eq!(result, vec![Bytes::from(&b"some\nawesome\nfile"[..])]);

        Ok(())
    }

    #[test]
    fn test_stream_dir() -> io::Result<()> {
        let tmp_dir = TempDir::new("test_stream_dir")?;

        for i in 1..=5 {
            let file_path = tmp_dir.path().join(format!("test_file{}.txt", i));
            let mut tmp_file = File::create(file_path)?;
            writeln!(tmp_file, "file{}\nwas{}\nhere{}", i, i, i)?;
        }

        let fut = stream_dir(tmp_dir.path().to_path_buf()).collect();

        let mut result = run(fut)?;
        result.sort();

        assert_eq!(
            result,
            vec![
                Bytes::from(&b"file1\nwas1\nhere1\n"[..]),
                Bytes::from(&b"file2\nwas2\nhere2\n"[..]),
                Bytes::from(&b"file3\nwas3\nhere3\n"[..]),
                Bytes::from(&b"file4\nwas4\nhere4\n"[..]),
                Bytes::from(&b"file5\nwas5\nhere5\n"[..])
            ]
        );

        Ok(())
    }
}
