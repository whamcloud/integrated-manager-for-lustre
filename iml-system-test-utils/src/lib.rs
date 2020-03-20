pub mod docker;
pub mod iml;
pub mod vagrant;

use std::{io, time::Duration};
use tokio::{process::Command, time::delay_for};

pub async fn try_command_n_times(max_tries: u32, cmd: &mut Command) -> Result<(), io::Error> {
    let mut count = 1;
    let mut r = cmd.status().await?;

    // try to run the command max_tries times until it succeeds. There is a delay of 1 second.
    while !r.success() && count < max_tries {
        println!("Trying command: {:?} - Attempt #{}", cmd, count + 1);
        count += 1;

        delay_for(Duration::from_secs(1)).await;

        r = cmd.status().await?;
    }

    if r.success() {
        Ok(())
    } else {
        Err(io::Error::new(
            io::ErrorKind::Other,
            format!(
                "Command {:?} failed to succeed after {} attempts.",
                cmd, max_tries
            ),
        ))
    }
}

pub fn get_local_server_names<'a>(servers: &'a [&'a str]) -> Vec<String> {
    servers
        .iter()
        .map(move |x| format!("{}.local", x))
        .collect()
}
