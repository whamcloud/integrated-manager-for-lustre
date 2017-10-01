[**Table of Contents**](index.md)

# Running SSI Tests
---

# MacOS
---


# Linux
---

# Windows
---

## Running IML tests on HPC cluster with Windows, Cygwin and Vagrant

## Description

Using Cygwin (*nix like interface on Windows), Vagrant and Virtualbox installed on Windows, run the IML source Makefile 'ssi_tests' target.

This will, in turn, first destroy any existing HPC cluster created by the makefile, then run the base Vagrantfile _intel-manager-for-lustre/Vagrantfile_ (with command _vagrant up_) to bring up a functional HPC cluster, before proceeding to run the tests.

## Windows environment

Specifications of my setup are as follows:
* Windows 8.1 Enterprise
* VirtualBox 5.1.26
* Vagrant 1.9.7
* Cygwin 2.8.2(0.313/5/3) x86_64

To setup, install the following packages:

* [Install Virtualbox](https://www.virtualbox.org/wiki/Downloads)
* [Install Vagrant](https://www.vagrantup.com/downloads.html) and then add Vagrant bin directory to system path
* [Install Cygwin](https://cygwin.com/install.html), selecting make, bash, git and vim packages and perform the relevant configuration of openssh network access (including proxies if needed)
* [Install Cygwin package manager](https://code.google.com/archive/p/apt-cyg/) (optional)

* Clone source
_git clone git@github.com:intel-hpdd/intel-manager-for-lustre.git_

* Bring up HPC
_cd intel-manager-for-lustre_
_make ssi\_tests_

# Troubleshooting and solutions

## Free space
Ensure at least 10 GB of free space is available

## Host-only interfaces
When setting up the cluster, I had issues when using multiple host-only, Virtualbox created, network interfaces. The workaround I used was to change my other, unrelated, VMs to use the same host-only interface as the HPC cluster (10.73.10.0/24).

## VBoxManage attachstorage --comment option
This option has now been removed from the base Vagrantfile, but in version 5.1.26 of Virtualbox on Windows, the _--comment_ of the _VBoxManage attachstorage_ command is not implemented and using it throws an error.

## Compiling pdsh (including dshbak) on Cygwin
Have to be compiled manually …

### install automake, libetool, autoconf, nc
### [download pdsh source](https://sourceforge.net/projects/pdsh/?source=typ_redirect)
### _./configure_ command gives cannot guess build type so ...
http://git.savannah.gnu.org/gitweb/?p=config.git;a=blob_plain;f=config.sub;hb=HEAD
http://git.savannah.gnu.org/gitweb/?p=config.git;a=blob_plain;f=config.guess;hb=HEAD
config.guess needs to be updated in package configure dir, copy from above locations into pdsh-2.26/configure/
### install gcc-{core,g++} libgcc1 gdb make
_./configure_ should then complete

### Building

in order to avoid the following errors:

$ /usr/local/bin/pdsh
pdsh@tanabarr-MOBL1: module path "/usr/local/lib/pdsh" insecure.
pdsh@tanabarr-MOBL1: "/usr/local/lib": Owner not root, current uid, or pdsh executable owner
pdsh@tanabarr-MOBL1: Couldn't load any pdsh modules

Run configure as follows:

_./configure --with-ssh --enable-static-modules --prefix=/home/`username` && make && make install_

Because we have installed in home dir, need to add /home/`username`/bin to system path, add the following to your .bashrc:

_export PATH=$PATH:/home/`username`/bin_

## Work around "stdout is not a tty" error when using vagrant cli
downgrade from vagrant 1.9.7->1.9.6

[https://github.com/mitchellh/vagrant/issues/8780](https://github.com/mitchellh/vagrant/issues/8780)

[https://github.com/mitchellh/vagrant/issues/8833](https://github.com/mitchellh/vagrant/issues/8833)

[https://github.com/mitchellh/vagrant/issues/8764](https://github.com/mitchellh/vagrant/issues/8764)

various commands failing within Makefile due to inability to parse output of vagrant cli calls
this is a bug and workaround is to use version 1.9.6 rather than the most recent 1.9.7

## Work around missing getaddrinfo in Cygwin

[https://cygwin.com/ml/cygwin/2006-02/msg00531.html](https://cygwin.com/ml/cygwin/2006-02/msg00531.html)

[http://pdplab.it.uom.gr/teaching/gcc_manuals/gnulib.html](http://pdplab.it.uom.gr/teaching/gcc_manuals/gnulib.html)

Getaddrinfo seems not to be the root issue and ssh to vms was failing because of '*' setting inside ~/.ssh/config which was overriding the vagrant settings. Ensure configurations do not conflict!

## References
* [https://stackoverflow.com/questions/4810996/how-to-resolve-configure-guessing-build-type-failure](https://stackoverflow.com/questions/4810996/how-to-resolve-configure-guessing-build-type-failure)
* [http://web.cecs.pdx.edu/~pkwong/ECE103_files/Resources/Compiler/C_GNU/GCC_Installation/How_to_Install_Cygwin+GCC.htm](ttp://web.cecs.pdx.edu/~pkwong/ECE103_files/Resources/Compiler/C_GNU/GCC_Installation/How_to_Install_Cygwin+GCC.htm)

* [https://sourceforge.net/p/pdsh/mailman/message/290492/](https://sourceforge.net/p/pdsh/mailman/message/290492/)