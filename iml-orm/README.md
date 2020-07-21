# IML ORM

An orm using [diesel](http://diesel.rs/).

This crate makes use of a few different feature flags for portability:

- `postgres-interop`

  Enable this feature to work with the diesel ORM / db.

- `wasm`

  Enable this feature to use the `models.rs` module from within WebAssembly.

By default this crate will _not_ have postgres support, only the model structs. The models all implement `Serialize` / `Deserialize`, so they can be used within other crates for uniform types.

## Getting started

1. Install diesel-cli on your machine.

```sh
# Ensure libpq is installed:
yum install postgresql-devel

# Install global cli tool (ensure /root/.cargo/bin is part of your PATH)
cargo install diesel_cli --no-default-features --features postgres
```

## Actions

The following are some actions you can do with the cli tool

- Print the current schema (excluding tables without primary key):

```sh
# only for RPM based install
diesel print-schema --database-url postgres://chroma@
```

- Generate models from the given schema (within `src` dir)

```sh
cargo install diesel_cli_ext
diesel_ext --add-table-name --model -M "Jsonb serde_json::Value" -M "Lustre_fid LustreFid" -M "SqlLustreFid LustreFid" > models.rs
```

## Background

This crate aims to centralize queries as much as possible. This allows for reuse between different downstream services.

Model specific implementations and free fns live directly under `src/`.
