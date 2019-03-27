// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::agent_error::ImlAgentError;
use futures::future::poll_fn;
use futures::prelude::*;
use std::{io::Write, path::Path};
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
    tokio::fs::File::open(p)
        .map_err(|e| e.into())
        .and_then(|file| {
            tokio::io::read_to_end(file, vec![])
                .map(|(_, d)| d)
                .map_err(|e| e.into())
        })
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
