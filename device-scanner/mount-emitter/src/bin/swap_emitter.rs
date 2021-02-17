// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use mount_emitter::{get_write_stream, line_to_command};
use std::{io::BufRead, time::Duration};
use tokio::{io::AsyncWriteExt, process::Command, time::sleep};
use tracing_subscriber::{fmt::Subscriber, EnvFilter};

#[tokio::main]
async fn main() -> Result<(), mount_emitter::Error> {
    let subscriber = Subscriber::builder()
        .with_env_filter(EnvFilter::from_default_env())
        .finish();

    tracing::subscriber::set_global_default(subscriber).unwrap();

    loop {
        let output = Command::new("/usr/bin/findmnt")
            .arg("-P")
            .arg("-s")
            .arg("-e")
            .arg("-t")
            .arg("swap")
            .output()
            .await?;

        if !output.status.success() {
            if Some(1) == output.status.code() {
                tracing::debug!("No swap entries found");
                continue;
            } else {
                return Err(mount_emitter::Error::Unexpected(format!(
                    "findmnt call failed. exit code: {:?}, stderr: {}",
                    output.status.code(),
                    String::from_utf8_lossy(&output.stderr)
                )));
            }
        }

        let xs: Vec<String> = (&output.stdout).lines().collect::<Result<_, _>>()?;

        tracing::debug!("Swap entries: {:?}", xs);

        for x in xs {
            let x = x.trim();

            if x == "" {
                continue;
            }

            let mount_command = line_to_command(x.as_bytes())?;

            let x =
                serde_json::to_string(&device_types::Command::MountCommand(mount_command))? + "\n";

            let mut s = get_write_stream()?;

            s.write_all(x.as_bytes()).await?;
        }

        tracing::debug!("Wrote entries");

        sleep(Duration::from_secs(60)).await;
    }
}
