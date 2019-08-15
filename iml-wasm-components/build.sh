#!/usr/bin/env bash
rm -rf package
cargo build --target wasm32-unknown-unknown --release
mkdir package
WASM_MODULE=package
wasm-bindgen target/wasm32-unknown-unknown/release/${WASM_MODULE}.wasm \
    --target no-modules \
    --out-dir ./package \
    --out-name ${WASM_MODULE}
