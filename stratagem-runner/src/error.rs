// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use liblustreapi::error::LiblustreError;
use std::{error, io, io::Error};

/// Encapsulates any errors that may happen while working with `stratagem`
#[derive(Debug)]
pub enum StratagemError {
    Io(std::io::Error),
    LiblustreError(LiblustreError),
    Utf8Error(std::str::Utf8Error),
    CsvError(csv::Error),
}

impl StratagemError {
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
}

impl std::fmt::Display for StratagemError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match *self {
            StratagemError::Io(ref err) => write!(f, "{}", err),
            StratagemError::LiblustreError(ref err) => write!(f, "{}", err),
            StratagemError::Utf8Error(ref err) => write!(f, "{}", err),
            StratagemError::CsvError(ref err) => write!(f, "{}", err),
        }
    }
}

impl std::error::Error for StratagemError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match *self {
            StratagemError::Io(ref err) => Some(err),
            StratagemError::LiblustreError(ref err) => Some(err),
            StratagemError::Utf8Error(ref err) => Some(err),
            StratagemError::CsvError(ref err) => Some(err),
        }
    }
}

impl From<Error> for StratagemError {
    fn from(err: Error) -> Self {
        StratagemError::Io(err)
    }
}

impl From<LiblustreError> for StratagemError {
    fn from(err: LiblustreError) -> Self {
        StratagemError::LiblustreError(err)
    }
}

impl From<std::str::Utf8Error> for StratagemError {
    fn from(err: std::str::Utf8Error) -> Self {
        StratagemError::Utf8Error(err)
    }
}

impl From<csv::Error> for StratagemError {
    fn from(err: csv::Error) -> Self {
        StratagemError::CsvError(err)
    }
}
