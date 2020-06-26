# IML Task Runner

## Purpose

This crate processes Fids in the FidTaskQueue (chroma_core_fidtaskqueue) table.
It runs the associated actions as specified on the linked Task
(chroma_core_task).

## Architecture

For each Worker (client mount) : Find Tasks that worker can run

For each Task found : Find some fids and process them

