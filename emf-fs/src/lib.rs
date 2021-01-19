// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::{io::AsyncBufReadExt, stream, Stream, StreamExt, TryFutureExt, TryStreamExt};
use std::{
    io::{self, Write},
    path::{Path, PathBuf},
};
use tempfile::NamedTempFile;
use tokio::{
    fs::{self, File},
    prelude::*,
    task::spawn_blocking,
};
use tokio_util::codec::{BytesCodec, FramedRead, FramedWrite, LinesCodec, LinesCodecError};

#[derive(Debug)]
pub enum EmfFsError {
    LinesCodecError(LinesCodecError),
    IoError(io::Error),
}

impl std::fmt::Display for EmfFsError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match *self {
            Self::LinesCodecError(ref err) => write!(f, "{}", err),
            Self::IoError(ref err) => write!(f, "{}", err),
        }
    }
}

impl std::error::Error for EmfFsError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match *self {
            Self::LinesCodecError(ref err) => Some(err),
            Self::IoError(ref err) => Some(err),
        }
    }
}

impl From<LinesCodecError> for EmfFsError {
    fn from(err: LinesCodecError) -> Self {
        Self::LinesCodecError(err)
    }
}

impl From<io::Error> for EmfFsError {
    fn from(err: io::Error) -> Self {
        Self::IoError(err)
    }
}

/// Given a `Stream` of items that implement `AsRef<[u8]>`, returns a stream
/// that reads line by line.
pub fn read_lines<
    'a,
    I: AsRef<[u8]> + 'a,
    E: Into<Box<dyn std::error::Error + Send + Sync>> + 'a,
>(
    s: impl Stream<Item = Result<I, E>> + Send + 'a,
) -> impl Stream<Item = Result<String, io::Error>> + 'a {
    s.boxed()
        .map_err(|e| io::Error::new(io::ErrorKind::Other, e))
        .into_async_read()
        .lines()
}

/// Given a path, attempts to do an async read to the end of the file.
///
/// # Arguments
///
/// * `p` - The `Path` to a file.
pub async fn read_file_to_end<P>(p: P) -> Result<Vec<u8>, io::Error>
where
    P: AsRef<Path> + Send,
{
    let mut file = File::open(p).await?;

    let mut contents = vec![];

    file.read_to_end(&mut contents).await?;

    Ok(contents)
}

/// Given a path, streams the file till EOF
///
/// # Arguments
///
/// * `p` - The `Path` to a file.
pub fn stream_file<P>(p: P) -> impl Stream<Item = Result<bytes::Bytes, EmfFsError>>
where
    P: AsRef<Path> + Send + 'static,
{
    File::open(p)
        .err_into()
        .map_ok(|file| FramedRead::new(file, BytesCodec::new()))
        .try_flatten_stream()
        .err_into()
        .map_ok(bytes::BytesMut::freeze)
}

/// Given a path, streams the file line by line till EOF
///
/// # Arguments
///
/// * `p` - The `Path` to a file.
pub fn stream_file_lines<P>(p: P) -> impl Stream<Item = Result<String, EmfFsError>>
where
    P: AsRef<Path> + Send + 'static,
{
    File::open(p)
        .err_into()
        .map_ok(|file| FramedRead::new(file, LinesCodec::new()))
        .try_flatten_stream()
        .err_into()
}

/// Given a directory of files,
/// stream each file line by line one at a time till EOF
///
/// # Arguments
///
/// * `p` - The `Path` to a directory.
pub fn stream_dir_lines<P>(p: P) -> impl Stream<Item = Result<String, EmfFsError>>
where
    P: AsRef<Path> + Send + 'static,
{
    tokio::fs::read_dir(p)
        .err_into()
        .try_flatten_stream()
        .map_ok(|d| d.path())
        .map_ok(stream_file_lines)
        .try_flatten()
}

/// Given a directory of files,
/// stream each file one at a time till EOF
///
/// # Arguments
///
/// * `p` - The `Path` to a directory.
pub fn stream_dir<P>(p: P) -> impl Stream<Item = Result<bytes::Bytes, EmfFsError>>
where
    P: AsRef<Path> + Send + 'static,
{
    tokio::fs::read_dir(p)
        .err_into()
        .try_flatten_stream()
        .map_ok(|d| d.path())
        .map_ok(stream_file)
        .try_flatten()
}

/// Given an iterator of directory of files,
/// stream each file one at a time till EOF
///
/// # Arguments
///
/// * `ps` - An `Iterator` of directory `Path`s.
pub fn stream_dirs<P>(
    ps: impl IntoIterator<Item = P>,
) -> impl Stream<Item = Result<bytes::Bytes, EmfFsError>>
where
    P: AsRef<Path> + Send + 'static,
{
    stream::iter(ps).map(stream_dir).flatten()
}

/// Creates a temporary file and writes some bytes to it.
pub async fn write_tempfile(contents: Vec<u8>) -> Result<NamedTempFile, io::Error> {
    spawn_blocking(move || {
        let mut f = NamedTempFile::new()?;

        f.write_all(contents.as_ref())?;

        Ok::<_, io::Error>(f)
    })
    .await?
}

/// Does the given path exist as a file?
pub async fn file_exists(path: impl AsRef<Path>) -> bool {
    let x = fs::metadata(path).await;

    match x {
        Ok(m) => m.is_file(),
        Err(_) => false,
    }
}

/// Does the given path exist as a directory?
pub async fn dir_exists(path: impl AsRef<Path>) -> bool {
    let x = tokio::fs::metadata(path).await;

    match x {
        Ok(m) => m.is_dir(),
        Err(_) => false,
    }
}

/// Given a `PathBuf`, Open for append or creates a new file that can have
/// arbitrary `Bytes` written to it.
pub async fn file_append_bytes(path: PathBuf) -> Result<FramedWrite<File, BytesCodec>, io::Error> {
    let file = fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(path)
        .await?;

    Ok(FramedWrite::new(file, BytesCodec::new()))
}

/// Given a `PathBuf`, creates a new file that can have
/// arbitrary `Bytes` written to it.
pub async fn file_write_bytes(path: PathBuf) -> Result<FramedWrite<File, BytesCodec>, io::Error> {
    let file = fs::File::create(path).await?;

    Ok(FramedWrite::new(file, BytesCodec::new()))
}

#[cfg(test)]
mod tests {
    use super::*;
    use bytes::Bytes;
    use futures::stream;
    use std::fs::File;
    use tempdir::TempDir;
    use tempfile::NamedTempFile;

    #[tokio::test]
    async fn test_read_lines() -> Result<(), EmfFsError> {
        let lines: Vec<_> = read_lines(stream::once(async { Ok::<_, io::Error>("foo\nbar\nbaz") }))
            .try_collect()
            .await?;

        assert_eq!(lines, vec!["foo", "bar", "baz"]);

        Ok(())
    }

    #[tokio::test]
    async fn test_write_tempfile() -> Result<(), EmfFsError> {
        let file = write_tempfile(b"foobar".to_vec()).await?;

        let s = std::fs::read_to_string(file.path())?;

        assert_eq!(s, "foobar");

        Ok(())
    }

    #[tokio::test]
    async fn test_stream_file() -> Result<(), EmfFsError> {
        let mut f = NamedTempFile::new()?;

        f.write_all(b"some\nawesome\nfile")?;

        let path = f.path().to_path_buf();

        let result: Vec<_> = stream_file(path).try_collect().await?;

        assert_eq!(result, vec![Bytes::from(&b"some\nawesome\nfile"[..])]);

        Ok(())
    }

    #[tokio::test]
    async fn test_stream_dir() -> Result<(), EmfFsError> {
        let tmp_dir = TempDir::new("test_stream_dir")?;

        for i in 1..=5 {
            let file_path = tmp_dir.path().join(format!("test_file{}.txt", i));
            let mut tmp_file = File::create(file_path)?;
            writeln!(tmp_file, "file{}\nwas{}\nhere{}", i, i, i)?;
        }

        let mut result: Vec<_> = stream_dir(tmp_dir.path().to_path_buf())
            .try_collect()
            .await?;
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
