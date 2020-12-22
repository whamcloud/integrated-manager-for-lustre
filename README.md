# EXAScaler Management Framework

Simple, but powerful, management tools that provide a unified, consistent view of Lustre storage systems and simplify the installation, configuration, monitoring, and overall management of Lustre.

## Dev Setup

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
cargo install sqlx-cli --no-default-features --features postgres --git https://github.com/launchbadge/sqlx --tag v0.4.2
```

Precommit checks are run by [rusty-hook](https://github.com/swellaby/rusty-hook). To setup do the following:

```sh
cargo install --git https://github.com/swellaby/rusty-hook.git
rusty-hook init # In this directory
```
