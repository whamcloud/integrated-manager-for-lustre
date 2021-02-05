#!/bin/sh -l

cd $WORKSPACE

if [ "$TASK" = "emf-exa-parser" ]; then
    cd emf-exa-parser
    cargo test -- --ignored
fi