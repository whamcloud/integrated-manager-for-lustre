pub mod docker;
pub mod iml;
pub mod systemd;
pub mod vagrant;

use futures::{future::BoxFuture, FutureExt, TryFutureExt};
use std::{io, process::ExitStatus};
use tokio::process::Command;

fn handle_status(x: ExitStatus) -> Result<(), io::Error> {
    if x.success() {
        Ok(())
    } else {
        let err = io::Error::new(
            io::ErrorKind::Other,
            format!("process exited with code: {:?}", x.code()),
        )
        .into();
        Err(err)
    }
}

pub trait CheckedStatus {
    fn checked_status(&mut self) -> BoxFuture<Result<(), io::Error>>;
}

impl CheckedStatus for Command {
    /// Similar to `status`, but returns `Err` if the exit code is non-zero.
    fn checked_status(&mut self) -> BoxFuture<Result<(), io::Error>> {
        println!("Running cmd: {:?}", self);

        self.status()
            .and_then(|x| async move { handle_status(x) })
            .boxed()
    }
}
