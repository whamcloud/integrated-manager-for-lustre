# EMF Agent

## Overview

The `emf-agent` crate is responsible for running tasks from the `emf-manager` and for periodically supplying data to the `emf-manager`.

Tasks sent by the manager are run with `action-plugins`.

Data sent to the manager are run in `daemon-plugins`.

Both agent and daemon plugins are efficiently run within a single process using a work-stealing thread pool and non-blocking IO.

## Action Plugins

Action plugins live in the `emf-agent/src/action_plugins` directory.

They are simple asynchronous functions that take in JSON deserializable data and return a `Result` of JSON serializable data or an Error.

Plugins _must_ be statically registered within [emf-agent/src/action_plugins/](https://github.com/whamcloud/exascaler-management-framework/blob/666bb150ff53ddf4901db96773b921942eee0ee8/emf-agent/src/action_plugins/action_plugin.rs).

### Example

The following is an extremely simple action plugin. It takes a file path and runs cat over it, returning the result. This is only for illustrative purposes.

```rust
pub async fn cat_file(path: String) -> Result<Vec<u8>, EmfAgentError> {
  let x = Command::new("cat").arg(path).output().await?;

  if x.status.success() {
    Ok(x.stdout)
  } else {
    Err(EmfAgentError::CmdOutputError(x))
  }
}
```

## Daemon Plugins

Daemon plugins live in the `emf-agent/src/daemon_plugins` directory.

Unlike action plugins, daemon plugins are stateful. They send an initial data payload to the manager on startup and then optionally send an update payload every 10 seconds. While action plugins are useful for management actions, daemon-plugins are useful for monitoring the distributed system.

If a daemon plugin exceeds it's default deadline of 1 second, it's task will be cancelled and rescheduled for the next poll. This deadline is configurable on a per-plugin basis.

A Daemon plugin _must_ implement the [`DaemonPlugin`](https://github.com/whamcloud/exascaler-management-framework/blob/666bb150ff53ddf4901db96773b921942eee0ee8/emf-agent/src/daemon_plugins/daemon_plugin.rs#L25-L50) trait. In additon, a `DaemonPlugin` must be statically registered to the daemon-plugin registry in [emf-agent/src/daemon_plugins/daemon_plugin.rs](https://github.com/whamcloud/exascaler-management-framework/blob/666bb150ff53ddf4901db96773b921942eee0ee8/emf-agent/src/daemon_plugins/daemon_plugin.rs).

Daemon plugins are run within a Session between the agent and the manager. As such, the plugin may be in one of the following states:

- `Active`: There is an active communication channel between the agent and manager
- `Pending`: A session create request has been sent to the manager and the agent awaiting a response
- `Empty`: There is no session or request for one between the agent and manager
