// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

//! Reads streaming mount information from stdin and forwards to `device-scanner` daemon.
//!
//! The `mount-emitter` crate uses `tokio` to stream stdin line by line, parse it
//! into a `MountCommand` variant and send the serialized result to `device-scanner`.
//!

use device_types::{
    mount::{FsType, MountCommand, MountOpts, MountPoint},
    Command, DevicePath,
};
use futures::Future;
use std::{collections::HashMap, convert::AsRef, os::unix::net::UnixStream as NetUnixStream, str};
use tokio::{
    io::{self, AsyncBufRead, AsyncBufReadExt, AsyncWrite, AsyncWriteExt},
    net::UnixStream,
};

#[derive(Debug, thiserror::Error)]
pub enum Error {
    #[error(transparent)]
    Io(#[from] std::io::Error),
    #[error(transparent)]
    SerdeJson(#[from] serde_json::Error),
    #[error(transparent)]
    Utf8Error(#[from] std::str::Utf8Error),
    #[error("missing {0}")]
    Missing(&'static str),
    #[error("unexpected {0}")]
    Unexpected(String),
}

pub fn line_to_command(x: &[u8]) -> Result<MountCommand, Error> {
    let mut x: IntermediateMap = line_to_hashmap(&x)?;

    let (target, source, fstype, mount_opts, old_opts, old_target) = (
        MountPoint(
            x.remove("TARGET")
                .ok_or_else(|| Error::Missing("TARGET"))?
                .into(),
        ),
        DevicePath(
            x.remove("SOURCE")
                .ok_or_else(|| Error::Missing("SOURCE"))?
                .into(),
        ),
        FsType(x.remove("FSTYPE").ok_or_else(|| Error::Missing("FSTYPE"))?),
        MountOpts(
            x.remove("OPTIONS")
                .ok_or_else(|| Error::Missing("OPTIONS"))?,
        ),
        x.get("OLD-OPTIONS"),
        x.get("OLD-TARGET"),
    );

    let x = match x.get("ACTION").map(AsRef::as_ref) {
        Some("mount") | None => MountCommand::AddMount(target, source, fstype, mount_opts),
        Some("umount") => MountCommand::RemoveMount(target, source, fstype, mount_opts),
        Some("remount") => MountCommand::ReplaceMount(
            target,
            source,
            fstype,
            mount_opts,
            MountOpts(
                old_opts
                    .ok_or_else(|| Error::Missing("OLD-OPTIONS"))?
                    .to_string(),
            ),
        ),
        Some("move") => MountCommand::MoveMount(
            target,
            source,
            fstype,
            mount_opts,
            MountPoint(
                old_target
                    .ok_or_else(|| Error::Missing("OLD-TARGET"))?
                    .into(),
            ),
        ),
        Some(x) => return Err(Error::Unexpected(x.to_string())),
    };

    Ok(x)
}

type IntermediateMap = HashMap<String, String>;

fn line_to_hashmap(x: &[u8]) -> Result<IntermediateMap, Error> {
    let x = str::from_utf8(x)?
        .trim()
        .split(' ')
        .fold(HashMap::new(), build_hashmap);

    Ok(x)
}

fn build_hashmap(mut acc: IntermediateMap, x: &str) -> IntermediateMap {
    let xs: Vec<&str> = x.splitn(2, '=').collect();

    let (k, v) = match xs.as_slice() {
        [k, v] => (k, v.trim_matches('"')),
        _ => panic!("Expected two matches from: {:?}", xs),
    };

    acc.insert((*k).to_string(), v.to_string());

    acc
}

/// Creates a stream that implements `AsyncWrite`
/// In this case, we use `tokio::net::UnixStream`,
/// But we can substitute this fn for integration testing
pub fn get_write_stream() -> Result<impl AsyncWrite, Error> {
    let stream = NetUnixStream::connect("/var/run/device-scanner.sock")?;

    let x = UnixStream::from_std(stream)?;

    Ok(x)
}

/// Writes a given buffer to the tokio runtime.
pub async fn write_all<A, T>(mut a: A, buf: T) -> Result<(), std::io::Error>
where
    A: AsyncWrite + std::marker::Unpin,
    T: AsRef<[u8]>,
{
    a.write_all(buf.as_ref()).await?;

    Ok(())
}

/// convert stdin into a nonblocking file;
pub fn stdin_to_file() -> impl AsyncBufRead {
    io::BufReader::new(io::stdin())
}

/// Loops over lines streaming from STDIN.
/// This has been extracted for integration
/// testing purposes.
pub async fn looper<R, R1, W, W1, F, W2>(
    read_fn: R,
    write_fn: W,
    write_out: W2,
) -> Result<(), Error>
where
    R: Fn() -> R1,
    R1: AsyncBufRead + std::marker::Unpin + Send + 'static,
    W: Fn() -> Result<W1, Error>,
    W1: AsyncWrite + Send + Sized + 'static,
    F: Future<Output = Result<(), std::io::Error>> + Send + 'static,
    W2: Fn(W1, String) -> F + Send + Sync + 'static,
{
    let mut file = read_fn();

    let mut line = vec![];

    loop {
        file.read_until(b'\n', &mut line).await?;

        tracing::debug!("Read line: {}", String::from_utf8_lossy(&line));

        if str::from_utf8(&line)? == "" {
            break;
        }

        let mount_command: MountCommand = line_to_command(&line)?;

        tracing::debug!("Parsed mount_command {:?}", mount_command);

        let x = serde_json::to_string(&Command::MountCommand(mount_command))?;

        let s = write_fn()?;

        let wo = write_out(s, x);

        wo.await?;

        tracing::debug!("Wrote line");

        if line.ends_with(b"\n") {
            line.clear();
        } else {
            break;
        };
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use insta::assert_debug_snapshot;

    type StableVec = Vec<(String, String)>;

    fn map_to_sorted_vec(x: IntermediateMap) -> StableVec {
        let mut xs: Vec<(String, String)> = x.into_iter().collect();

        xs.sort();

        xs
    }

    #[test]
    fn test_line_to_hashmap_swap() {
        let line = b"TARGET=\"swap\" SOURCE=\"/dev/mapper/centos-swap\" FSTYPE=\"swap\" OPTIONS=\"defaults\"\n";

        assert_debug_snapshot!(map_to_sorted_vec(line_to_hashmap(line).unwrap()))
    }

    #[test]
    fn test_line_to_hashmap_mount() {
        let line = b"ACTION=\"mount\" TARGET=\"/mnt/part1\" SOURCE=\"/dev/sde1\" FSTYPE=\"ext4\" OPTIONS=\"rw,relatime,data=ordered\" OLD-TARGET=\"\" OLD-OPTIONS=\"\"\n";

        assert_debug_snapshot!(map_to_sorted_vec(line_to_hashmap(line).unwrap()))
    }

    #[test]
    fn test_swap() {
        let line = b"TARGET=\"swap\" SOURCE=\"/dev/mapper/centos-swap\" FSTYPE=\"swap\" OPTIONS=\"defaults\"\n";

        assert_debug_snapshot!(line_to_command(line).unwrap())
    }

    #[test]
    fn test_poll_mount() {
        let line = b"ACTION=\"mount\" TARGET=\"/mnt/part1\" SOURCE=\"/dev/sde1\" FSTYPE=\"ext4\" OPTIONS=\"rw,relatime,data=ordered\" OLD-TARGET=\"\" OLD-OPTIONS=\"\"\n";

        assert_debug_snapshot!(line_to_command(line).unwrap())
    }

    #[test]
    fn test_poll_umount() {
        let line = b"ACTION=\"umount\" TARGET=\"/testPool4\" SOURCE=\"testPool4\" FSTYPE=\"zfs\" OPTIONS=\"rw,xattr,noacl\" OLD-TARGET=\"\" OLD-OPTIONS=\"\"\n";

        assert_debug_snapshot!(line_to_command(line).unwrap())
    }

    #[test]
    fn test_poll_remount() {
        let line = b"ACTION=\"remount\" TARGET=\"/mnt/part1\" SOURCE=\"/dev/sde1\" FSTYPE=\"ext4\" OPTIONS=\"ro,relatime,data=ordered\" OLD-TARGET=\"\" OLD-OPTIONS=\"rw,data=ordered\"\n";

        assert_debug_snapshot!(line_to_command(line).unwrap())
    }

    #[test]
    fn test_poll_move() {
        let line = b"ACTION=\"move\" TARGET=\"/mnt/part1a\" SOURCE=\"/dev/sde1\" FSTYPE=\"ext4\" OPTIONS=\"rw,relatime,data=ordered\" OLD-TARGET=\"/mnt/part1\" OLD-OPTIONS=\"\"\n";

        assert_debug_snapshot!(line_to_command(line).unwrap())
    }

    #[test]
    fn test_list_mount() {
        let line = b"TARGET=\"/mnt/part1\" SOURCE=\"/dev/sde1\" FSTYPE=\"ext4\" OPTIONS=\"rw,relatime,data=ordered\"\n";

        assert_debug_snapshot!(line_to_command(line).unwrap())
    }

    #[test]
    fn test_swap_extra() {
        let line = b"TARGET=\"swap\" SOURCE=\"/dev/mapper/VolGroup00-LogVol01\" FSTYPE=\"swap\" OPTIONS=\"defaults\"";

        assert_debug_snapshot!(line_to_command(line).unwrap())
    }
}
