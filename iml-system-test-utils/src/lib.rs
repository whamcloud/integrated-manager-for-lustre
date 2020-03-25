pub mod docker;
pub mod iml;
pub mod vagrant;

use futures::{future::BoxFuture, FutureExt, TryFutureExt};
use std::{io, process::ExitStatus, thread, time};
use tokio::process::Command;

fn handle_status(x: ExitStatus) -> Result<(), io::Error> {
    if x.success() {
        Ok(())
    } else {
        let err = io::Error::new(
            io::ErrorKind::Other,
            format!("process exited with code: {:?}", x.code()),
        );
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

pub async fn try_command_n_times(max_tries: u32, cmd: &mut Command) -> Result<(), io::Error> {
    let mut count = 0;
    let one_sec = time::Duration::from_millis(1000);

    let mut r = cmd.status().await?;

    // try to run the command max_tries times until it succeeds. There is a delay of 1 second.
    while !r.success() && count < max_tries {
        count += 1;

        thread::sleep(one_sec);

        r = cmd.status().await?;
    }

    if r.success() {
        Ok(())
    } else {
        Err(io::Error::new(io::ErrorKind::Other, format!("Command {:?} failed to succeed after {} attempts.", cmd, max_tries)))
    }
}
