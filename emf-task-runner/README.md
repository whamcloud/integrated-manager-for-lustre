# EMF Task Runner

## Purpose

This crate runs work assigned to Tasks. It polls work from the database, and
parcels it out to the available workers.

## Architecture

A Task is specific type of work (purges from lpurge, or mirror extends from lamigo).
Work is generated and passed up to the database through emf-mailbox.

This crate processes Fids in the FidTaskQueue (fidtaskqueue) table.
It runs the associated actions as specified on the linked Task
(task) on an available worker.

The process is as follows:

    For each Worker (client mount) -> Find Tasks that worker can run
      For each Task found -> Find some fids and process them
