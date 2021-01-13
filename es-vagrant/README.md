# Vagrantfiles

## Setup EMF with Vagrant and VirtualBox

The EMF Team typically uses [Vagrant](https://www.vagrantup.com) and [VirtualBox](https://www.virtualbox.org/wiki/Downloads) for day to day development tasks. The following guide will provide an overview of how to setup a development environment from scratch.

1. Install Exascaler vbox from [EXA Packer](https://github.com/whamcloud/exa-packer/)

1. Clone the [Exascaler Management Framework repo](https://github.com/whamcloud/exascaler-management-framework/) from Github

1. Navigate to the `exascaler-management-framework/es-vagrant` directory

### MacOS

1. Install Homebrew

   [Homebrew](https://brew.sh/) provides a package manager for macos. We will use this to install dependencies in the following steps. See the [Homebrew](https://brew.sh) website for installation instructions.

1. Install Vagrant and VirtualBox

   Using the `brew cask` command:

   ```sh
   brew cask install vagrant virtualbox
   ```

1. Create the default hostonlyif needed by the cluster:

   ```sh
   VBoxManage hostonlyif create
   ```

1. Bring up the cluster (4 exascaler nodes, 2 el7 client nodes, 1 ubuntu client node)

   ```sh
   vagrant up
   vagrant provision --provision-with=es-install
   vagrant provision --provision-with=ha-setup,start-lustre
   ```

1. (optional) Install New EMF.

   1. Local docker RPM (install from `cd ..; make docker-rpms`)

   ```sh
   make docker-local
   ```
   
1. Setup EMF

   ```sh
   vagrant provision --provision-with=create-esui
   ```

1. Teardown EMF

   ```sh
   vagrant provision --provision-with=destroy-esui
   ```

1. Setup the clients (`install-lustre-client` on ubuntu clients involves building lustre client from source)

   ```sh
   vagrant provision --provision-with=install-lustre-client,configure-lustre-client-network
   ```

1. Get sosreport

   ```sh
   vagrant provision --provision-with=create-sosreport
   ```

1. Mount the clients:

   - Primary Filesystem

     ```sh
     vagrant provision --provision-with=mount-lustre-client
     ```

At this point you should be able to access the EMF GUI on your host at https://localhost:8443
