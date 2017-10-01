[**Table of Contents**](index.md)

# Creating a Monitored Only Lustre zfs Filesystem on Vagrant HPC Storage Sandbox

![zfs](md_Graphics/monitored_filesystem_sm.jpg)

## Prerequisites:
Please refer to https://github.com/intel-hpdd/vagrantfiles on how to create a virtual HPC storage cluster with vagrant before attempting to install IML.

## Download IML build, create zfs installer, and install zfs packages:
Note: use vagrant ssh-config to get the port each server is running on. The commands below use ports that are specific to my vagrant environment. 
1. Verify the following vagrant plugins are installed:
    ```
    vagrant plugin install vagrant-shell-commander
    ```
2. Download the latest IML build (tarball). For example, the preview 3 build 
from: [https://github.com/intel-hpdd/intel-manager-for-lustre/releases/download/v4.0.0.0P3/iml-4.0.0.0.tar.gz](https://github.com/intel-hpdd/intel-manager-for-lustre/releases/download/v4.0.0.0P3/iml-4.0.0.0.tar.gz)

3. Create zfs installer and install the zfs packages on the following servers: mds1, mds2, oss1, and oss2
   ```
       cd ~/downloads
       tar xzvf iml-4.0.0.0.tar.gz
       cd iml-4.0.0.0
       ./create_installer zfs
       for i in {2200..2203}; do scp -P $i ~/Downloads/iml-4.0.0.0/lustre-zfs-el7-installer.tar.gz vagrant@127.0.0.1:/tmp/.; done
       # password is "vagrant"
       vagrant sh -c 'cd /tmp; sudo tar xzvf lustre-zfs-el7-installer.tar.gz; cd lustre-zfs; sudo ./install' mds1 mds2 oss1 oss2
   ```


## Installing IML:

1.  Copy the IML build to the /tmp directory in your admin node:
    ```
    scp -P 2222 ~/Downloads/iml-4.0.0.0.tar.gz vagrant@127.0.0.1:/tmp/.
    # password is "vagrant"
    ```
2. ssh into the admin box and install the build:
    ```
    vagrant ssh
    [vagrant@adm ~]$ sudo su - # (or "sudo -s")
    [vagrant@adm ~]# cd /tmp
    [vagrant@adm ~]# tar xvf <buildname>.tar.gz
    [vagrant@adm ~]# cd <build folder>
    [vagrant@adm ~]# ./install --no-dbspace-check
    ```
3. Update the /etc/hosts file on your computer to include the following line:
    ```
    127.0.0.1 adm.lfs.local
    ```
4. Test that a connection can be made to IML by going to the following link in your browser:
https://adm.lfs.local:8443

## Adding and Configuring Servers
You should now be able to see IML when navigating to https://adm.lfs.local:8443. Click on the login link at the top right and log in as the admin. Next, go to the server configuration page and add the following servers:
```
mds[1,2].lfs.local,oss[1,2].lfs.local
# Make sure to select "Monitored Server Profile" for the servers profile
```
This will take some time (around 5 to 10 minutes) but all four servers should add successfully.
There will be alters and warnings about LNET. Ignore for now.

Once all servers have been added with "Monitored Server Profile", each server will need to know which interface should be assigned the lustre network.
ssh to each server (mds1, mds2, oss1, oss2)
vagrant ssh <server>  and as root (sudo su ) run the following commands:
```
    systemctl stop firewalld ; systemctl disable firewalld 
    systemctl stop NetworkManager; systemctl disable NetworkManager 
    systemctl start ntpd 
    echo 'options lnet networks=tcp0(enp0s9)' > /etc/modprobe.d/lustre.conf 
    modprobe lnet 
    lctl network configure 
    /sbin/modprobe zfs
    genhostid
```

The IML GUI should show that the LNET and NID Configuration is updated (IP Address 10.73.20.x to use `Lustre Network 0`). All alerts are cleared.


## Creating a monitored only zfs based Lustre filesystem

The lustre filesystem will be created from the command line on zpools and IML GUI will be used to scan for the filesytem.
Note that VM Disks (ata-VBOX_HARDDISK...) will be mapped as /dev/sd devices. Use "ls -l /dev/disk/by-id/" to list the VM Disks available. 

- Management Target:
```
    vagrant ssh mds1
    sudo -s
    #note use /dev/sdb (512M) for the mgt
    zpool create mgs -o cachefile=none /dev/disk/by-id/ata-VBOX_HARDDISK_VBe85051d4-e6ae953d -f
    mkfs.lustre --reformat --failover mds2.lfs.local@tcp --mgs --backfstype=zfs mgs/mgt
    mkdir -p /lustre/mgs
    mount -t lustre mgs/mgt /lustre/mgs
```

- Metadata Target:
```
    vagrant ssh mds2
    sudo -s
    zpool create mds -o cachefile=none /dev/disk/by-id/ata-VBOX_HARDDISK_VB0729fac1-5420a643 -f
    mkfs.lustre --reformat --failover mds1.lfs.local@tcp  --mdt --backfstype=zfs --fsname=zfsmo --index=0 --mgsnode=mds1.lfs.local@tcp mds/mdt0
    mkdir -p /lustre/zfsmo/mdt0
    mount -t lustre mds/mdt0 /lustre/zfsmo/mdt0
```
- Object Storage Targets:
```
    vagrant ssh oss1
    sudo -s
    zpool create oss1 -o cachefile=none raidz2 /dev/disk/by-id/ata-VBOX_HARDDISK_VB6f41df02-0d5d2a15 /dev/disk/by-id/ata-VBOX_HARDDISK_VB06b563a9-2539af7b  /dev/disk/by-id/ata-VBOX_HARDDISK_VBb2ec79fb-b900b724 /dev/disk/by-id/ata-VBOX_HARDDISK_VBe2585d74-5267121b -f
    mkfs.lustre --reformat --failover oss2.lfs.local@tcp  --ost --backfstype=zfs --fsname=zfsmo --index=0 --mgsnode=mds1.lfs.local@tcp oss1/ost00
    zfs compression=on oss1
    mkdir -p /lustre/zfsmo/ost00
    mount -t lustre oss1/ost00 /lustre/zfsmo/ost00

    vagrant ssh oss2
    sudo -s
    zpool create oss2 -o cachefile=none raidz2 /dev/disk/by-id/ata-VBOX_HARDDISK_VBb7776d10-aba16176 /dev/disk/by-id/ata-VBOX_HARDDISK_VB6657241f-bab2ffed  /dev/disk/by-id/ata-VBOX_HARDDISK_VB0ebfc209-9bbf80c4 /dev/disk/by-id/ata-VBOX_HARDDISK_VB51449aa2-95df9cdc -f
    mkfs.lustre --reformat --failover oss1.lfs.local@tcp  --ost --backfstype=zfs --fsname=zfsmo --index=1 --mgsnode=mds1.lfs.local oss2/ost01
    zfs compression=on oss2
    mkdir -p /lustre/zfsmo/ost01
    mount -t lustre oss2/ost01 /lustre/zfsmo/ost01
```

After all the commands for each node had run successfully, use the IML GUI to scan for the filesystem:
    Configuration -> Servers -> Scan for Filesystem.  Use all servers

If Successful, in the IML GUI, the filesystem will be available.

## [Setting up Clients](IML_Setting_up_Clients.md)
