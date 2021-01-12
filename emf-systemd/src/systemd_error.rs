use emf_cmd::CmdError;
use std::{fmt, process::Output};

#[derive(Debug)]
pub struct RequiredError(pub String);

impl fmt::Display for RequiredError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "{:?}", self.0)
    }
}

impl std::error::Error for RequiredError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        None
    }
}

#[derive(Debug)]
pub enum SystemdError {
    Io(std::io::Error),
    Utf8Error(std::str::Utf8Error),
    RequiredError(RequiredError),
    CmdError(CmdError),
    UnexpectedStatusError,
}

impl std::fmt::Display for SystemdError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match *self {
            SystemdError::Io(ref err) => write!(f, "{}", err),
            SystemdError::Utf8Error(ref err) => write!(f, "{}", err),
            SystemdError::RequiredError(ref err) => write!(f, "{}", err),
            SystemdError::CmdError(ref err) => write!(f, "{}", err),
            SystemdError::UnexpectedStatusError => write!(f, "Unexpected status code"),
        }
    }
}

impl std::error::Error for SystemdError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match *self {
            SystemdError::Io(ref err) => Some(err),
            SystemdError::Utf8Error(ref err) => Some(err),
            SystemdError::RequiredError(ref err) => Some(err),
            SystemdError::CmdError(ref err) => Some(err),
            SystemdError::UnexpectedStatusError => None,
        }
    }
}

impl From<std::io::Error> for SystemdError {
    fn from(err: std::io::Error) -> Self {
        SystemdError::Io(err)
    }
}

impl From<std::str::Utf8Error> for SystemdError {
    fn from(err: std::str::Utf8Error) -> Self {
        SystemdError::Utf8Error(err)
    }
}

impl From<RequiredError> for SystemdError {
    fn from(err: RequiredError) -> Self {
        SystemdError::RequiredError(err)
    }
}

impl From<Output> for SystemdError {
    fn from(output: Output) -> Self {
        SystemdError::CmdError(output.into())
    }
}

impl From<CmdError> for SystemdError {
    fn from(err: CmdError) -> Self {
        SystemdError::CmdError(err)
    }
}
