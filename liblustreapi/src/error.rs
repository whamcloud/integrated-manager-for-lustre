// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::LIBLUSTRE;
use std::{error, ffi::IntoStringError, io};
use thiserror::Error;

/// Error if liblustreapi.so calls fail to load
#[derive(Debug, Clone)]
pub struct LoadError {
    msg: String,
}

impl std::fmt::Display for LoadError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        write!(f, "{} failed to load: {}", LIBLUSTRE, self.msg)
    }
}

impl std::error::Error for LoadError {
    fn source(&self) -> Option<&(dyn error::Error + 'static)> {
        None
    }
}

impl From<io::Error> for LoadError {
    fn from(err: io::Error) -> Self {
        LoadError::new(format!("{}", err))
    }
}

impl LoadError {
    pub fn new(s: String) -> LoadError {
        LoadError { msg: s }
    }

    pub fn into_raw(self) -> String {
        self.msg
    }
}

/// Encapsulates any errors that may happen while working with `liblustreapi`
#[derive(Debug, Error)]
pub enum LiblustreError {
    #[error(transparent)]
    Io(#[from] std::io::Error),
    #[error(transparent)]
    IntoString(#[from] IntoStringError),
    #[error(transparent)]
    NulError(#[from] std::ffi::NulError),
    #[error(transparent)]
    LibLoadingError(#[from] libloading::Error),
}

impl LiblustreError {
    pub fn not_found<E>(e: E) -> Self
    where
        E: Into<Box<dyn error::Error + Send + Sync>>,
    {
        io::Error::new(io::ErrorKind::NotFound, e).into()
    }
    pub fn invalid_input<E>(e: E) -> Self
    where
        E: Into<Box<dyn error::Error + Send + Sync>>,
    {
        io::Error::new(io::ErrorKind::InvalidInput, e).into()
    }
    pub fn os_error(e: i32) -> Self {
        io::Error::from_raw_os_error(e).into()
    }
    pub fn no_mntpt() -> Self {
        io::Error::from_raw_os_error(libc::ENXIO).into()
    }
}
