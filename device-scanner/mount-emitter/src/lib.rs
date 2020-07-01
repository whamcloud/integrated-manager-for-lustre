// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

//! Reads streaming mount information from stdin and forwards to `device-scanner` daemon.
//!
//! The `mount-emitter` crate uses `tokio` to stream stdin line by line, parse it
//! into a `MountCommand` variant and send the serialized result to `device-scanner`.
//!

use std::convert::AsRef;

use device_types::{
    mount::{FsType, MountCommand, MountOpts, MountPoint},
    Command, DevicePath,
};
use futures::{future, Future};
use std::{
    collections::HashMap, io::BufRead, os::unix::net::UnixStream as NetUnixStream, process::exit,
    str,
};
use tokio::{
    io::{AsyncRead, AsyncWrite},
    net::UnixStream,
    reactor::Handle,
};

fn line_to_command(x: &[u8]) -> MountCommand {
    let mut x: IntermediateMap = line_to_hashmap(&x);

    let (target, source, fstype, mount_opts, old_opts, old_target) = (
        MountPoint(x.remove("TARGET").expect("missing TARGET").into()),
        DevicePath(x.remove("SOURCE").expect("missing SOURCE").into()),
        FsType(x.remove("FSTYPE").expect("missing FSTYPE")),
        MountOpts(x.remove("OPTIONS").expect("missing OPTIONS")),
        x.get("OLD-OPTIONS"),
        x.get("OLD-TARGET"),
    );

    match x.get("ACTION").map(AsRef::as_ref) {
        Some("mount") | None => MountCommand::AddMount(target, source, fstype, mount_opts),
        Some("umount") => MountCommand::RemoveMount(target, source, fstype, mount_opts),
        Some("remount") => MountCommand::ReplaceMount(
            target,
            source,
            fstype,
            mount_opts,
            MountOpts(old_opts.expect("missing OLD-OPTIONS").to_string()),
        ),
        Some("move") => MountCommand::MoveMount(
            target,
            source,
            fstype,
            mount_opts,
            MountPoint(old_target.expect("missing OLD-TARGET").into()),
        ),
        Some(x) => {
            eprintln!("Unexpected ACTION: {}", x);
            exit(1);
        }
    }
}

type IntermediateMap = HashMap<String, String>;

fn line_to_hashmap(x: &[u8]) -> IntermediateMap {
    str::from_utf8(x)
        .expect("Did not convert from utf8")
        .trim()
        .split(' ')
        .fold(HashMap::new(), build_hashmap)
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
pub fn get_write_stream() -> impl AsyncWrite {
    let stream = NetUnixStream::connect("/var/run/device-scanner.sock")
        .expect("Unable to connect to device-scanner.sock");

    UnixStream::from_std(stream, &Handle::default()).expect("Unable to consume device-scanner.sock")
}

/// Writes a given buffer to the tokio runtime.
pub fn write_all<A, T>(a: A, buf: T) -> impl Future<Item = (), Error = std::io::Error>
where
    A: AsyncWrite,
    T: AsRef<[u8]>,
{
    tokio::io::write_all(a, buf).map(|_| ())
}

/// convert stdin into a nonblocking file;
/// this is the only part that makes use of tokio_file_unix
pub fn stdin_to_file() -> impl AsyncRead + BufRead {
    let file = tokio_file_unix::raw_stdin().unwrap();
    let file = tokio_file_unix::File::new_nb(file).unwrap();
    file.into_reader(&Handle::default()).unwrap()
}

/// Loops over lines streaming from STDIN.
/// This has been extracted for integration
/// testing purposes.
pub fn looper<R, R1, W, W1, F, W2>(
    read_fn: R,
    write_fn: W,
    write_out: W2,
) -> impl Future<Item = (), Error = ()>
where
    R: Fn() -> R1,
    R1: AsyncRead + BufRead + Send + 'static,
    W: Fn() -> W1 + Send + 'static,
    W1: AsyncWrite + Send + Sized + 'static,
    F: Future<Item = (), Error = std::io::Error> + Send + 'static,
    W2: Fn(W1, String) -> F + Send + Sync + 'static,
{
    let file = read_fn();

    future::loop_fn(
        (file, Vec::new(), write_fn, write_out),
        |(file, line, write_fn, write_out)| {
            // read each line
            tokio::io::read_until(file, b'\n', line).and_then(|(file, mut line)| {
                if str::from_utf8(&line).unwrap() == "" {
                    return future::Either::A(future::done(Ok(future::Loop::Break(()))));
                }

                let mount_command: MountCommand = line_to_command(&line);

                let x = serde_json::to_string(&Command::MountCommand(mount_command))
                    .expect("Could not serialize mount command");

                let s = write_fn();

                let wo = write_out(s, x);

                let next = if line.ends_with(b"\n") {
                    line.clear();
                    future::Loop::Continue((file, line, write_fn, write_out))
                } else {
                    future::Loop::Break(())
                };

                future::Either::B(wo.map(|_| next))
            })
        },
    )
    .map_err(|e| panic!("{:?}", e))
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

        assert_debug_snapshot!(map_to_sorted_vec(line_to_hashmap(line)))
    }

    #[test]
    fn test_line_to_hashmap_mount() {
        let line = b"ACTION=\"mount\" TARGET=\"/mnt/part1\" SOURCE=\"/dev/sde1\" FSTYPE=\"ext4\" OPTIONS=\"rw,relatime,data=ordered\" OLD-TARGET=\"\" OLD-OPTIONS=\"\"\n";

        assert_debug_snapshot!(map_to_sorted_vec(line_to_hashmap(line)))
    }

    #[test]
    fn test_swap() {
        let line = b"TARGET=\"swap\" SOURCE=\"/dev/mapper/centos-swap\" FSTYPE=\"swap\" OPTIONS=\"defaults\"\n";

        assert_debug_snapshot!(line_to_command(line))
    }

    #[test]
    fn test_poll_mount() {
        let line = b"ACTION=\"mount\" TARGET=\"/mnt/part1\" SOURCE=\"/dev/sde1\" FSTYPE=\"ext4\" OPTIONS=\"rw,relatime,data=ordered\" OLD-TARGET=\"\" OLD-OPTIONS=\"\"\n";

        assert_debug_snapshot!(line_to_command(line))
    }

    #[test]
    fn test_poll_umount() {
        let line = b"ACTION=\"umount\" TARGET=\"/testPool4\" SOURCE=\"testPool4\" FSTYPE=\"zfs\" OPTIONS=\"rw,xattr,noacl\" OLD-TARGET=\"\" OLD-OPTIONS=\"\"\n";

        assert_debug_snapshot!(line_to_command(line))
    }

    #[test]
    fn test_poll_remount() {
        let line = b"ACTION=\"remount\" TARGET=\"/mnt/part1\" SOURCE=\"/dev/sde1\" FSTYPE=\"ext4\" OPTIONS=\"ro,relatime,data=ordered\" OLD-TARGET=\"\" OLD-OPTIONS=\"rw,data=ordered\"\n";

        assert_debug_snapshot!(line_to_command(line))
    }

    #[test]
    fn test_poll_move() {
        let line = b"ACTION=\"move\" TARGET=\"/mnt/part1a\" SOURCE=\"/dev/sde1\" FSTYPE=\"ext4\" OPTIONS=\"rw,relatime,data=ordered\" OLD-TARGET=\"/mnt/part1\" OLD-OPTIONS=\"\"\n";

        assert_debug_snapshot!(line_to_command(line))
    }

    #[test]
    fn test_list_mount() {
        let line = b"TARGET=\"/mnt/part1\" SOURCE=\"/dev/sde1\" FSTYPE=\"ext4\" OPTIONS=\"rw,relatime,data=ordered\"\n";

        assert_debug_snapshot!(line_to_command(line))
    }

    #[test]
    fn test_swap_extra() {
        let line = b"TARGET=\"swap\" SOURCE=\"/dev/mapper/VolGroup00-LogVol01\" FSTYPE=\"swap\" OPTIONS=\"defaults\"";

        assert_debug_snapshot!(line_to_command(line))
    }
}
