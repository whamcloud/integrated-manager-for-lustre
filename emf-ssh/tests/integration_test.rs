mod common;

use emf_ssh::{SshChannelExt as _, SshHandleExt as _};

#[tokio::test]
async fn test_successful_remote_command() -> Result<(), Box<dyn std::error::Error>> {
    common::start_server(2222).await?;

    let mut handle = common::connect(2222).await?;
    let channel = handle.create_channel().await?;
    let mut child = channel.spawn(&"echo This is a test!").await?;

    let mut reader = child.stdout.take().unwrap();
    let buf = String::new();
    let (buf_tx, buf_rx) = tokio::sync::oneshot::channel::<String>();
    tokio::spawn(async move {
        common::read_into_buffer(&mut reader, buf, buf_tx).await;
    });

    let exit_code = child.wait().await?;

    let buf_val = buf_rx.await?;

    assert_eq!(buf_val, "stdout: This is a test!");
    assert_eq!(exit_code, 0);

    Ok(())
}

#[tokio::test]
async fn test_remote_command_errored() -> Result<(), Box<dyn std::error::Error>> {
    common::start_server(2223).await?;

    let mut handle = common::connect(2223).await?;
    let channel = handle.create_channel().await?;
    let mut child = channel.spawn(&"ls unknown-file").await?;

    let mut reader = child.stderr.take().unwrap();
    let buf = String::new();
    let (buf_tx, buf_rx) = tokio::sync::oneshot::channel::<String>();
    tokio::spawn(async move {
        common::read_into_buffer(&mut reader, buf, buf_tx).await;
    });

    let exit_code = child.wait().await?;

    let buf_val = buf_rx.await?;

    assert!(buf_val.contains("stderr: ls:"));
    // Return code on OS X is 1
    // Return code on linux is 2
    assert!(vec![1, 2].contains(&exit_code));

    Ok(())
}

// This will be re-enabled when https://nest.pijul.com/pijul/thrussh/discussions/28 lands.
// #[tokio::test]
// async fn test_aborting_a_command() -> Result<(), Box<dyn std::error::Error>> {
//     emf_tracing::init();
//     common::start_server().await?;

//     let mut handle = common::connect().await?;
//     let channel = handle.create_channel().await?;

//     let mut child = channel.spawn(&"sleep 2").await.unwrap();

//     child.kill();

//     let exit_code = child.wait().await?;

//     assert_eq!(exit_code, 2);

//     Ok(())
// }
