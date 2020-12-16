# Integrated Manager For Lustre

[![Join the chat at https://gitter.im/whamcloud/integrated-manager-for-lustre](https://badges.gitter.im/whamcloud/integrated-manager-for-lustre.svg)](https://gitter.im/whamcloud/integrated-manager-for-lustre?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

[![Build Status](https://travis-ci.com/whamcloud/integrated-manager-for-lustre.svg?branch=master)](https://travis-ci.com/whamcloud/integrated-manager-for-lustre)

![iml-rust](https://github.com/whamcloud/integrated-manager-for-lustre/workflows/iml-rust/badge.svg)

![IML GUI](https://github.com/whamcloud/integrated-manager-for-lustre/workflows/IML%20GUI/badge.svg)

![Device Scanner CI](https://github.com/whamcloud/integrated-manager-for-lustre/workflows/Device%20Scanner%20CI/badge.svg)

Simple, but powerful, management tools that provide a unified, consistent view of Lustre storage systems and simplify the installation, configuration, monitoring, and overall management of Lustre.

## Docs

<https://whamcloud.github.io/Online-Help/>

A local db is required only when making changes to the SQLx queries in this repo.
In order to interact with a running database add a `.env` file in this directory with a `DATABASE_URL` environment variable.
For example, to connect to a local chroma db running on localhost the `.env` file would look like:

```sh
DATABASE_URL=postgres://chroma@localhost:5432/chroma
```

Once a change has been made to a query, run the following in this directory:

```sh
cargo sqlx prepare --merged -- --tests
```

You can check if the generated queries are up to date with:

```sh
cargo sqlx prepare --merged --check -- --tests
```

You may need to install the sqlx-cli as well:

```sh
cargo install sqlx-cli --no-default-features --features postgres --git https://github.com/jgrund/sqlx --branch workspace-support
```

Precommit checks are run by [rusty-hook](https://github.com/swellaby/rusty-hook). To setup do the following:

```sh
cargo install --git https://github.com/swellaby/rusty-hook.git
rusty-hook init # In this directory
```
