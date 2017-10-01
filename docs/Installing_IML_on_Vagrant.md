[**Table of Contents**](index.md)

# Installing IML on Vagrant

![clustre](md_Graphics/installing_sm.jpg)

## Prerequisites:
Please refer to [https://github.com/intel-hpdd/vagrantfiles](https://github.com/intel-hpdd/vagrantfiles) on how to create a virtual HPC storage cluster with vagrant before attempting to install IML.

* If the above instructions are already understood and VirtualBox and Vagrant are currently installed:
    * Move to the desired working directory.
    * `git clone git@github.com:intel-hpdd/Vagrantfiles.git`
    * `cp Vagrantfiles/hpc-storage-sandbox-el7/* .`

* If running on a system with low memory, e.g., 8GB of RAM, edit the file: `Vagrantfile` and change the following:
    * Change: `vbx.memory = 1024` to `vbx.memory = 800`
    * Change: `v.memory = 2048` to `v.memory = 1536`
    

## Notes:
- You will be logging into your vagrant box as the vagrant user, which has the ability to run with root privilege. To elevate privileges to the root account, use the sudo command. The vagrant user does not require a password to run sudo. Should there ever be a need to login as root directly, the root password is also "vagrant". 

    To acquire a root shell, use sudo in either one of the following invocations:
    ```
    sudo -s
    ```
    or
    ```
    sudo su -
    ```

## Installing IML:
1. Verify that the following vagrant plugins are installed:
    ```
    vagrant plugin list

    vagrant plugin install vagrant-shell-commander
    vagrant plugin install vagrant-share
    vagrant plugin install vagrant-vbguest
    vagrant plugin install vagrant-proxyconf    <--- Optional, for example, this may be needed if behind corporate firewall.
    ```
2. Obtain the [preview 3 build](https://github.com/intel-hpdd/intel-manager-for-lustre/releases/tag/v4.0.0.0P3).
3. Exit from the vagrant box and scp the build to the /tmp directory in your admin node. For example, if your admin node is running on port 2200 (you can verify this with `vagrant ssh-config`) and the build is in your Downloads folder:
    ```
    scp -P 2200 ~/Downloads/iml-4.0.0.0.tar.gz vagrant@127.0.0.1:/tmp/.
    # password is "vagrant"
    ```
    Alternatively, use the output of `vagrant ssh-config` to create a temporary SSH configuration for the `scp` command. This is most useful when there will be a lot of interaction with a node from outside the VM:
    ```
    [user@mini iml]$ vagrant ssh-config | tee sshcfg| grep ^Host
    Host adm
    Host mds1
    ...
    [user@mini iml]$ scp -F sshcfg ~/Downloads/iml-4.0.0.0.tar.gz adm:/tmp/.
    iml-4.0.0.0.tar.gz                                                 100%  130MB  69.5MB/s   00:01    
    ```
    This allows you to use the Host name referenced in the ssh config to identify individual nodes in the Vagrant environment, and means you do not have to track the port numbers or use a password. In the above example, the file is copied on to the `adm` VM.

4. ssh into the admin box and install the build:
    ```
    vagrant ssh
    [vagrant@adm ~]$ sudo su - # (or "sudo -s")
    [vagrant@adm ~]# cd /tmp
    [vagrant@adm ~]# tar xvzf <buildname>.tar.gz
    [vagrant@adm ~]# cd <build folder>
    [vagrant@adm ~]# ./install --no-dbspace-check
    ```
5. Update the /etc/hosts file on your computer to include the following line:
    ```
    127.0.0.1 adm.lfs.local
    ```
6. Finally, test that a connection can be made to IML by going to the following link in your browser:
https://adm.lfs.local:8443

## Adding Servers
You should now be able to see IML when navigating to https://adm.lfs.local:8443. Click on the login link at the top right and log in as the admin. Next, go to the server configuration page and add the following servers:
```
mds[1,2].lfs.local,oss[1,2].lfs.local
```
This will take some time (around 20 to 30 minutes) but all four servers should add successfully.

## Configuring Interfaces
Once all servers have been added, each server will need to know which interface should be assigned the lustre network. Navigate to each server detail page by clicking on the server link. Scroll to the bottom of the server detail page where you will see a list of network interfaces. Click on the `Configure` button and you will be given the option to change the network driver and the network for each interface. 

The vagrant file indicates that the lustre network will run on 10.73.20.x. If `Lustre Network 0` is specified for a different IP address, you will need to change its interface to `Not Lustre Network` and update the network for 10.73.20.x to use `Lustre Network 0`. It is very important that Lustre Network 0 is specified on the correct interface; otherwise, creating a filesystem will fail. Make sure that all servers have been updated where appropriate.

## Creating a Filesystem
To create a filesystem, simply navigate to `Configure->File Systems` and click the `Create` button. Make the following selections:
- Management Target / MGS -> mds1 (512 MB)
- Metadata Target / MDS -> mds2
- Object Storage Targets -> Select ALL OSS nodes

After the selections have been made, click the button to create the filesystem. If you have any issues creating the filesystem there is a good chance that the interface for 10.73.20.x is not assigned to Lustre Network 0. If this happens, stop the filesystem and update the interfaces accordingly. 

## [Setting up Clients](IML_Setting_up_Clients.md)
