// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

#[derive(Debug)]
pub enum Error {
    NotFound,
    Postgres(emf_postgres::Error),
}

impl std::error::Error for Error {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match *self {
            Error::NotFound => None,
            Error::Postgres(ref err) => Some(err),
        }
    }
}

impl std::fmt::Display for Error {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match *self {
            Error::NotFound => write!(f, "Not Found"),
            Error::Postgres(ref err) => write!(f, "{}", err),
        }
    }
}

impl From<emf_postgres::Error> for Error {
    fn from(err: emf_postgres::Error) -> Self {
        Error::Postgres(err)
    }
}
