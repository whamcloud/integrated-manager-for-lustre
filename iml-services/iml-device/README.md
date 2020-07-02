# IML Device

This crate consumes changes from device agent daemon plugins and persists them to the database.

It uses SQLx for data persistence.

A local db is required only when making changes to the queries in this crate.
In order to interact with a running database add a `.env` file in this directory with a `DATABASE_URL` environment variable.
For example, to connect to a local chroma db running on localhost the `.env` file would look like:

```sh
DATABASE_URL=postgres://chroma@localhost:5432/chroma
```

Once a change has been made to a query, run the following in this directory:

```sh
cargo sqlx prepare -- --bin iml-device
```

You may need to install the sqlx-cli as well:

```sh
cargo install sqlx-cli --no-default-features --features postgres --git https://github.com/launchbadge/sqlx
```
