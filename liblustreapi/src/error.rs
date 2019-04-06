// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use std::{error, ffi::IntoStringError, io, io::Error};

/// Encapsulates any errors that may happen while working with `liblustreapi`
#[derive(Debug)]
pub enum LiblustreError {
    Io(std::io::Error),
    IntoString(IntoStringError),
    NulError(std::ffi::NulError),
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
}

impl std::fmt::Display for LiblustreError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match *self {
            LiblustreError::Io(ref err) => write!(f, "{}", err),
            LiblustreError::IntoString(ref err) => write!(f, "{}", err),
            LiblustreError::NulError(ref err) => write!(f, "{}", err),
        }
    }
}

impl std::error::Error for LiblustreError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match *self {
            LiblustreError::Io(ref err) => Some(err),
            LiblustreError::IntoString(ref err) => Some(err),
            LiblustreError::NulError(ref err) => Some(err),
        }
    }
}

impl From<Error> for LiblustreError {
    fn from(err: Error) -> Self {
        LiblustreError::Io(err)
    }
}

impl From<IntoStringError> for LiblustreError {
    fn from(err: IntoStringError) -> Self {
        LiblustreError::IntoString(err)
    }
}

impl From<std::ffi::NulError> for LiblustreError {
    fn from(err: std::ffi::NulError) -> Self {
        LiblustreError::NulError(err)
    }
}
