#! /usr/bin/env bash

trailer=$(docker service ps -f 'name=iml_iml-manager-cli.1' iml_iml-manager-cli -q --no-trunc | head -n1)
TTYOPT=$(tty -s && echo "-t")
ENVOPT=""
if [ -n "$RUST_LOG" ]; then
	ENVOPT="-e RUST_LOG=$RUST_LOG"
fi

docker exec -i $TTYOPT $ENVOPT iml_iml-manager-cli.1.$trailer /usr/local/bin/iml "${@:1}"
