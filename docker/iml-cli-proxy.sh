#! /usr/bin/env bash

trailer=$(docker service ps -f 'name=iml_iml-manager-cli.1' iml_iml-manager-cli -q --no-trunc | head -n1)
TTYOPT=$(tty -s && echo "-t")

docker exec -i $TTYOPT iml_iml-manager-cli.1.$trailer iml "${@:1}"
