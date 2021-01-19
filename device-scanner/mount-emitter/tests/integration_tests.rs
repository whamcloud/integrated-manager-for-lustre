// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

extern crate futures;
extern crate mount_emitter;
extern crate tokio;

use mount_emitter::looper;
use std::sync::{Arc, Mutex};
use tokio::io;

enum Expect {
    One(&'static str),
    Many(Vec<&'static str>),
}

async fn server_test(x: &'static [u8], y: Expect) -> Result<(), mount_emitter::Error> {
    let ys = Arc::new(Mutex::new(match y {
        Expect::One(y) => vec![y].into_iter(),
        Expect::Many(ys) => ys.into_iter(),
    }));

    let f = looper(
        move || io::BufReader::new(x),
        || Ok(io::sink()),
        move |_, x| {
            let ys = ys.clone();

            async move {
                let y = ys
                    .lock()
                    .unwrap()
                    .next()
                    .expect("Did not get a test for given iteration");

                assert_eq!(x, *y);

                Ok(())
            }
        },
    );

    f.await
}

#[tokio::test]
async fn test_move_cmd() -> Result<(), mount_emitter::Error> {
    server_test(b"ACTION=\"move\" TARGET=\"/mnt/part1a\" SOURCE=\"/dev/sde1\" FSTYPE=\"ext4\" OPTIONS=\"rw,relatime,data=ordered\" OLD-TARGET=\"/mnt/part1\" OLD-OPTIONS=\"\"", Expect::One("{\"MountCommand\":{\"MoveMount\":[\"/mnt/part1a\",\"/dev/sde1\",\"ext4\",\"rw,relatime,data=ordered\",\"/mnt/part1\"]}}")).await
}

#[tokio::test]
async fn test_swap_cmd() -> Result<(), mount_emitter::Error> {
    server_test(b"TARGET=\"swap\" SOURCE=\"/dev/mapper/centos-swap\" FSTYPE=\"swap\" OPTIONS=\"defaults\"\n", Expect::One("{\"MountCommand\":{\"AddMount\":[\"swap\",\"/dev/mapper/centos-swap\",\"swap\",\"defaults\"]}}")).await
}

#[tokio::test]
async fn test_polling_cmd() -> Result<(), mount_emitter::Error> {
    let x = b"ACTION=\"mount\" TARGET=\"/testPool4\" SOURCE=\"testPool4\" FSTYPE=\"zfs\" OPTIONS=\"rw,xattr,noacl\" OLD-TARGET=\"\" OLD-OPTIONS=\"\"
        ACTION=\"mount\" TARGET=\"/testPool4/home\" SOURCE=\"testPool4/home\" FSTYPE=\"zfs\" OPTIONS=\"rw,xattr,noacl\" OLD-TARGET=\"\" OLD-OPTIONS=\"\"
        ACTION=\"umount\" TARGET=\"/testPool4/home\" SOURCE=\"testPool4/home\" FSTYPE=\"zfs\" OPTIONS=\"rw,xattr,noacl\" OLD-TARGET=\"/testPool4/home\" OLD-OPTIONS=\"rw,xattr,noacl\"
        ACTION=\"umount\" TARGET=\"/testPool4\" SOURCE=\"testPool4\" FSTYPE=\"zfs\" OPTIONS=\"rw,xattr,noacl\" OLD-TARGET=\"/testPool4\" OLD-OPTIONS=\"rw,xattr,noacl\"";

    let expected = vec![
        r#"{"MountCommand":{"AddMount":["/testPool4","testPool4","zfs","rw,xattr,noacl"]}}"#,
        r#"{"MountCommand":{"AddMount":["/testPool4/home","testPool4/home","zfs","rw,xattr,noacl"]}}"#,
        r#"{"MountCommand":{"RemoveMount":["/testPool4/home","testPool4/home","zfs","rw,xattr,noacl"]}}"#,
        r#"{"MountCommand":{"RemoveMount":["/testPool4","testPool4","zfs","rw,xattr,noacl"]}}"#,
    ];

    server_test(x, Expect::Many(expected)).await
}
