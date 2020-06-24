// Copyright (c) 2018 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use device_types::zed::ZedCommand;
use std::{env, error, fmt, io, io::prelude::*, os::unix::net::UnixStream};

pub type Result<T> = std::result::Result<T, Error>;

#[derive(Debug)]
pub enum Error {
    SerdeJson(serde_json::Error),
    Io(io::Error),
    Var(env::VarError),
}

impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match *self {
            Error::Io(ref err) => write!(f, "{}", err),
            Error::SerdeJson(ref err) => write!(f, "{}", err),
            Error::Var(ref err) => write!(f, "{}", err),
        }
    }
}

impl error::Error for Error {
    fn cause(&self) -> Option<&dyn error::Error> {
        match *self {
            Error::Io(ref err) => Some(err),
            Error::SerdeJson(ref err) => Some(err),
            Error::Var(ref err) => Some(err),
        }
    }
}

impl From<serde_json::Error> for Error {
    fn from(err: serde_json::Error) -> Self {
        Error::SerdeJson(err)
    }
}

impl From<io::Error> for Error {
    fn from(err: io::Error) -> Self {
        Error::Io(err)
    }
}

impl From<env::VarError> for Error {
    fn from(err: env::VarError) -> Self {
        Error::Var(err)
    }
}

pub fn send_data(z: ZedCommand) -> Result<()> {
    let x = serde_json::to_string(&z)?;

    let mut stream = UnixStream::connect("/var/run/zed-enhancer.sock")?;

    stream.write_all(x.as_bytes())?;

    Ok(())
}

pub mod zpool {
    use super::Error;
    use device_types::zed::zpool;
    use std::env;

    pub fn get_name() -> Result<zpool::Name, Error> {
        env::var("ZEVENT_POOL").map(zpool::Name).map_err(Error::Var)
    }

    pub fn get_guid() -> Result<zpool::Guid, Error> {
        env::var("ZEVENT_POOL_GUID")
            .map(zpool::Guid)
            .map_err(Error::Var)
    }

    pub fn get_state() -> Result<zpool::State, Error> {
        env::var("ZEVENT_POOL_STATE_STR")
            .map(zpool::State)
            .map_err(Error::Var)
    }
}

pub mod zfs {
    use super::Error;
    use device_types::zed::zfs;
    use std::env;

    pub fn get_name() -> Result<zfs::Name, Error> {
        env::var("ZEVENT_HISTORY_DSNAME")
            .map(zfs::Name)
            .map_err(Error::Var)
    }
}

pub mod vdev {
    use super::Error;
    use std::env;

    pub fn get_guid() -> Result<String, Error> {
        env::var("ZEVENT_VDEV_GUID").map_err(Error::Var)
    }

    pub fn get_state() -> Result<String, Error> {
        env::var("ZEVENT_VDEV_STATE_STR").map_err(Error::Var)
    }
}

pub mod zed {
    use super::Error;
    use device_types::zed::prop;
    use std::env;

    fn get_key_value(x: String) -> Result<(prop::Key, prop::Value), env::VarError> {
        let xs: Vec<&str> = x.split('=').collect();

        match &xs[..] {
            [a, b] => Ok((prop::Key((*a).to_string()), prop::Value((*b).to_string()))),
            _ => Err(env::VarError::NotPresent),
        }
    }

    pub fn get_history_string() -> Result<(prop::Key, prop::Value), Error> {
        env::var("ZEVENT_HISTORY_INTERNAL_STR")
            .and_then(get_key_value)
            .map_err(Error::Var)
    }

    pub enum HistoryEvent {
        Create,
        Destroy,
        Set,
    }

    pub fn get_history_name() -> Result<HistoryEvent, Error> {
        let x = env::var("ZEVENT_HISTORY_INTERNAL_NAME")?;

        match x.as_ref() {
            "create" => Ok(HistoryEvent::Create),
            "destroy" => Ok(HistoryEvent::Destroy),
            "set" => Ok(HistoryEvent::Set),
            _ => Err(Error::Var(env::VarError::NotPresent)),
        }
    }
}
