// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::agent_error::ImlAgentError;
use futures::{future::poll_fn, Future, Stream};
use std::{
    io::{BufReader, Write},
    path::Path,
};
use tempfile::NamedTempFile;
use tokio_threadpool::blocking;

/// Given a path, attempts to do an async read to the end of the file.
///
/// # Arguments
///
/// * `p` - The `Path` to a file.
pub fn read_file_to_end<P>(p: P) -> impl Future<Item = Vec<u8>, Error = ImlAgentError>
where
    P: AsRef<Path> + Send + 'static,
{
    tokio::fs::File::open(p).from_err().and_then(|file| {
        tokio::io::read_to_end(file, vec![])
            .map(|(_, d)| d)
            .from_err()
    })
}

/// Given a path, streams the file line by line till EOF
/// 
/// # Arguments
///
/// * `p` - The `Path` to a file.
pub fn stream_file<P>(p: P) -> impl Stream<Item = String, Error = ImlAgentError>
where
    P: AsRef<Path> + Send + 'static,
{
    tokio::fs::File::open(p)
        .map(|file| tokio::io::lines(BufReader::new(file)))
        .flatten_stream()
        .from_err()
}

/// Given a directory of files,
/// stream each file one at a time till EOF
/// 
/// # Arguments
///
/// * `p` - The `Path` to a directory.
pub fn stream_dir<P>(p: P) -> impl Stream<Item = String, Error = ImlAgentError>
where
    P: AsRef<Path> + Send + 'static,
{
    tokio::fs::read_dir(p)
        .flatten_stream()
        .map(|d| d.path())
        .map(stream_file)
        .flatten()
}

/// Creates a temporary file and writes some bytes to it.
pub fn write_tempfile(
    contents: Vec<u8>,
) -> impl Future<Item = NamedTempFile, Error = ImlAgentError> {
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

#[cfg(test)]
mod tests {
    use super::{stream_dir, stream_file, write_tempfile};
    use crate::agent_error::Result;
    use futures::{Future, Stream as _};
    use std::{fs::File, io::Write as _};
    use tempdir::TempDir;
    use tempfile::NamedTempFile;

    fn run<R: Send + 'static, E: Send + 'static>(
        fut: impl Future<Item = R, Error = E> + Send + 'static,
    ) -> std::result::Result<R, E> {
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
    fn test_stream_file() -> Result<()> {
        let mut f = NamedTempFile::new()?;

        f.write_all(b"some\nawesome\nfile")?;

        let path = f.path().to_path_buf();

        let fut = stream_file(path).collect();

        let result = run(fut)?;

        assert_eq!(result, vec!["some", "awesome", "file"]);

        Ok(())
    }

    #[test]
    fn test_stream_dir() -> Result<()> {
        let tmp_dir = TempDir::new("test_stream_dir")?;

        for i in 1..=5 {
            let file_path = tmp_dir.path().join(format!("test_file{}.txt", i));
            let mut tmp_file = File::create(file_path)?;
            writeln!(tmp_file, "file{}\nwas{}\nhere{}", i, i, i)?;
        }

        let fut = stream_dir(tmp_dir.path().to_path_buf()).collect();

        let result = run(fut)?;

        assert_eq!(
            result,
            vec![
                "file2", "was2", "here2", "file3", "was3", "here3", "file1", "was1", "here1",
                "file4", "was4", "here4", "file5", "was5", "here5"
            ]
        );

        Ok(())
    }
}
