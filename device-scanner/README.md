# device-scanner

This repo provides:

- a [persistent daemon](device-scanner-daemon) That holds block devices, ZFS devices, and device mounts in memory.
- a [binary](uevent-listener) that emits UEvents for block-device changes as they occur.
- a [binary](mount-emitter) that emits device mount changes as they occur.

## Architecture

    ┌───────────────┐ ┌───────────────┐
    │  Udev Script  │ │    ZEDlet     │
    └───────────────┘ └───────────────┘
            │                 │
            └────────┬────────┘
                     ▼
          ┌─────────────────────┐
          │ Unix Domain Socket  │
          └─────────────────────┘
                     │
                     ▼
       ┌───────────────────────────┐
       │   Device Scanner Daemon   │
       └───────────────────────────┘
                     │
                     ▼
          ┌─────────────────────┐
          │ Unix Domain Socket  │
          └─────────────────────┘
                     │
                     ▼
           ┌──────────────────┐
           │ Consumer Process │
           └──────────────────┘

## Development Dependencies

- [rust](https://www.rust-lang.org/)
- [ZFS](https://zfsonlinux.org/) Optional

## Development setup

- (Optional) [Install ZFS](https://zfsonlinux.org/) via OS package manager
- Install Rust deps: `cargo build`

### Building

#### Local

- `cargo build`

  To interact with the device-scanner in real time the following command can be used to keep the stream open such that updates can be seen as the data changes:

  ```sh
  cat - | ncat -U /var/run/device-scanner.sock | jq
  ```

  If interaction is not required, device info can be retrieved from the device-scanner by running the following command:

  ```sh
  echo '"Stream"' | socat - UNIX-CONNECT:/var/run/device-scanner.sock | jq
  ```

### Testing

- `cargo test`
