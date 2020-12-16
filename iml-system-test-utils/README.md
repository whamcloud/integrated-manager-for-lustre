# Integration Testing Overview

The system level tests are broken up into two types:

1. RPM-based integration tests
1. Docker-based integration tests

Both tests rely on the system level testing architecture described in this document. In general, there are two paths an integration test can take when testing the creation of a lustre filesystem in IML:

1. ldiskfs
1. stratagem

For information on how to run the integration tests, see the README.md for both the RPM and Docker system tests.

## Architecture

One of the benefits to using virtual machines is that they provide the ability to take snapshots. These snapshots can be leveraged at different points in time and allow new tests to start closer to their end state, thereby saving time. This approach leads to a di-graph based architecture in which the nodes represent the test states and the weighted edges encapsulate the logic to transition from one state to the next.

When a test runs the virtual machines will halt at certain times during the progression of the test and snapshots will be taken of each vm. These snapshots will build out the states of the graph. When a new test is invoked, it will parse the snapshot tree and find the snapshot state closest to the tests end state. This state will mark the starting point for the test and the snapshots of the vms will be restored to this point. The test will proceed from this state until it reaches its end state, following its specified path.

Since a lustre filesystem can be created in multiple ways, tests will naturally be split by their path. This path is the key to determine which direction a test will take when going from one node to the next:

The `use_stratagem` property indicates if the test will take the stratagem path.

## Adding Functionality

The edges of the graph hold the functionality to transition from one state to another. These edges are defined in `snapshots.rs`. To add new functionality to a test, simply add the new state and edge to the snapshots module and make sure that the `Transition` defined in the graph's edge points to the function that will perform the task. If a test's path includes the defined state it will perform the operation defined in the edge.

## Viewing the current graph

A unit test is provided in _snapshots.rs_ that will generate _dot_ output of the graph. This dot output can then be piped into graphviz where an image of the graph will be generated. Use the following command to run the test and get the dot output:

```sh
cargo test test_generate_graph_dot_file -- --nocapture
```
