// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::channel::mpsc::TrySendError;
use std::{error, fmt, io, num, result};
use tokio_util::codec::LinesCodecError;

pub type Result<T> = result::Result<T, Error>;

pub fn none_error<E>(error: E) -> Error
where
    E: Into<Box<dyn error::Error + Send + Sync>>,
{
    Error::NoneError(error.into())
}

#[derive(Debug)]
pub enum Error {
    Io(io::Error),
    TrySendError(Box<dyn error::Error + Send>),
    SerdeJson(serde_json::Error),
    LinesCodecError(LinesCodecError),
    ParseIntError(num::ParseIntError),
    NoneError(Box<dyn error::Error + Send + Sync>),
}

impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match *self {
            Error::Io(ref err) => write!(f, "{}", err),
            Error::TrySendError(ref err) => write!(f, "{}", err),
            Error::SerdeJson(ref err) => write!(f, "{}", err),
            Error::LinesCodecError(ref err) => write!(f, "{}", err),
            Error::ParseIntError(ref err) => write!(f, "{}", err),
            Error::NoneError(ref err) => write!(f, "{}", err),
        }
    }
}

impl error::Error for Error {
    fn cause(&self) -> Option<&dyn error::Error> {
        match *self {
            Error::Io(ref err) => Some(err),
            Error::TrySendError(_) => None,
            Error::SerdeJson(ref err) => Some(err),
            Error::LinesCodecError(ref err) => Some(err),
            Error::ParseIntError(ref err) => Some(err),
            Error::NoneError(_) => None,
        }
    }
}

impl From<io::Error> for Error {
    fn from(err: io::Error) -> Self {
        Error::Io(err)
    }
}

impl From<LinesCodecError> for Error {
    fn from(err: LinesCodecError) -> Self {
        Error::LinesCodecError(err)
    }
}

impl<E> From<TrySendError<E>> for Error
where
    E: Send + 'static,
{
    fn from(err: TrySendError<E>) -> Self {
        Error::TrySendError(Box::new(err))
    }
}

impl From<serde_json::Error> for Error {
    fn from(err: serde_json::Error) -> Self {
        Error::SerdeJson(err)
    }
}

impl From<num::ParseIntError> for Error {
    fn from(err: num::ParseIntError) -> Self {
        Error::ParseIntError(err)
    }
}
