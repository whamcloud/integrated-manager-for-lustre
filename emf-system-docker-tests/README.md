# EMF System Docker Tests

The system level Docker integration tests focus on the creation of various forms of Docker-based lustre filesystems. Vagrant is used to launch the following virtual machines:

1. iscsi - Used for filesystem devices
1. adm - Where docker will be running
1. mds[1,2] - The MDS nodes
1. oss[1,2] - The OSS nodes
1. c[1-8] - The client nodes

## Installation

Install the following software:

1. cargo
1. rust
1. Virtualbox
1. Vagrant

Once installed, the tests can be run out of the *emf-system-docker-tests* directory. Note that docker is **not** required to be installed on the host as it will be installed on the *adm* virtual machine. For information on testing architecture, please see README.md under *emf-system-test-utils*.

## Running Tests

There are multiple options that can be used when running the tests:

1. Local Install - This method will compile the software and install it on the manager node. While this method takes longer, it will ensure that the manager software is installed off of a local git branch:

    ```bash
    # To run all tests
    cargo test -- --test-threads=1 --nocapture 
    # To run a single test
    cargo test <test_name> -- --nocapture
    ```

1. REPO_URI Install - This method is faster and is recommended when the project has been built and is being hosted with an available repo url.

    ```bash
     # To run all tests
    REPO_URI=<repo url> cargo test -- --test-threads=1 --nocapture 
    # To run a single test
    REPO_URI=<repo url> cargo test <test_name> -- --nocapture
    ```