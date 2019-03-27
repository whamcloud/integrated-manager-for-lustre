#!/usr/bin/env bash
rm -rf package
cargo build --target wasm32-unknown-unknown --release
mkdir package
wasm-bindgen target/wasm32-unknown-unknown/release/iml_action_dropdown.wasm --no-modules --out-dir ./package --out-name package