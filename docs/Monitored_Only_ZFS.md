[**Table of Contents**](index.md)

# Creating a Monitored Only Lustre zfs Filesystem on Vagrant HPC Storage Sandbox

## Prerequisites:
Please refer to https://github.com/intel-hpdd/vagrantfiles on how to create a virtual HPC storage cluster with vagrant before attempting to install IML.

## Download IML build, create zfs installer, and install zfs packages:
Note: use vagrant ssh-config to get the port each server is running on. The commands below use ports that are specific to my vagrant environment. 
1. Verify the following vagrant plugins are installed:
    ```
    vagrant plugin install vagrant-shell-commander
    ```
2. Download the latest IML build (tarball). For example, the preview 2 build 
fromhttps://github.com/intel-hpdd/intel-manager-for-lustre/releases/download/v4.0.0.0P2/iml-4.0.0.0.tar.gz

3. Install epel-release and configure necessary repos on each virtual machine:
    ```
    vagrant sh -c '\
    sudo yum -y install epel-release && \
    sudo yum-config-manager --add-repo https://copr.fedorainfracloud.org/coprs/managerforlustre/manager-for-lustre/repo/epel-7/managerforlustre-manager-for-lustre-epel-7.repo && \
    sudo yum-config-manager --add-repo http://mirror.centos.org/centos/7/extras/x86_64/ && \
    sudo ed <<EOF /etc/yum.repos.d/mirror.centos.org_centos_7_extras_x86_64_.repo
    /enabled/a
    gpgcheck=1
    gpgkey=http://mirror.centos.org/centos/RPM-GPG-KEY-CentOS-7
    .
    wq
    EOF
    '
    ```

   ```
   vagrant sh -c '\
   sudo yum-config-manager --add-repo https://build.whamcloud.com/lustre-b2_10_last_successful_server/ && \
   sudo sed -i -e "1d" -e "2s/^.*$/[lustre]/" -e "/baseurl/s/,/%2C/g" -e "/enabled/a gpgcheck=0" /etc/yum.repos.d/build.whamcloud.com_lustre-b2_10_last_successful_server_.repo && \
   sudo yum-config-manager --add-repo https://downloads.hpdd.intel.com/public/e2fsprogs/latest/el7/ && \
   sudo sed -i -e "1d" -e "2s/^.*$/[e2fsprogs]/" -e "/baseurl/s/,/%2C/g" -e "/enabled/a gpgcheck=0" /etc/yum.repos.d/downloads.hpdd.intel.com_public_e2fsprogs_latest_el7_.repo
   ' mds1 mds2 oss1 oss2
   ```


4.  Create zfs installer and install the zfs packages on the following servers: mds1, mds2, oss1, and oss2
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
    [vagrant@ct7-adm ~]$ sudo su - # (or "sudo -s")
    [vagrant@ct7-adm ~]# cd /tmp
    [vagrant@ct7-adm ~]# tar xvf <buildname>.tar.gz
    [vagrant@ct7-adm ~]# cd <build folder>
    [vagrant@ct7-adm ~]# ./install --no-dbspace-check
    ```
3. Update the /etc/hosts file on your computer to include the following line:
    ```
    127.0.0.1 ct7-adm.lfs.local
    ```
4. Test that a connection can be made to IML by going to the following link in your browser:
https://ct7-adm.lfs.local:8443

## Adding and Configuring Servers
You should now be able to see IML when navigating to https://ct7-adm.lfs.local:8443. Click on the login link at the top right and log in as the admin. Next, go to the server configuration page and add the following servers:
```
ct7-mds[1,2].lfs.local,ct7-oss[1,2].lfs.local
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

The IML GUI should show that the LNET and NID Configuration is updated (IP Address 10.73.20.x to use `Lustre Network 0`). All alets are cleared.


## Creating a monitored only zfs based Lustre filesystem

The lustre filesystem will be created from the command line on zpools and IML GUI will be used to scan for the filesytem.
Note that VM Disks (ata-VBOX_HARDDISK...) will be mapped as /dev/sd devices. Use "ls -l /dev/disk/by-id/" to list the VM Disks available. 

- Management Target:
```
    vagrant ssh mds1
    sudo -s
    #note use /dev/sdb (512M) for the mgt
    zpool create mgs -o cachefile=none /dev/disk/by-id/ata-VBOX_HARDDISK_VBe85051d4-e6ae953d -f
    mkfs.lustre --reformat --failover 10.73.20.12@tcp --mgs --backfstype=zfs mgs/mgt
    mkdir -p /lustre/mgs
    mount -t lustre mgs/mgt /lustre/mgs
```

- Metadata Target:
```
    vagrant ssh mds2
    sudo -s
    zpool create mds -o cachefile=none /dev/disk/by-id/ata-VBOX_HARDDISK_VB0729fac1-5420a643 -f
    mkfs.lustre --reformat --failover 10.73.20.11@tcp  --mdt --backfstype=zfs --fsname=zfsmo --index=0 --mgsnode=10.73.20.11@tcp mds/mdt0
    mkdir -p /lustre/zfsmo/mdt0
    mount -t lustre mds/mdt0 /lustre/zfsmo/mdt0
```
- Object Storage Targets:
```
    vagrant ssh oss1
    sudo -s
    zpool create oss1 -o cachefile=none raidz2 /dev/disk/by-id/ata-VBOX_HARDDISK_VB6f41df02-0d5d2a15 /dev/disk/by-id/ata-VBOX_HARDDISK_VB06b563a9-2539af7b  /dev/disk/by-id/ata-VBOX_HARDDISK_VBb2ec79fb-b900b724 /dev/disk/by-id/ata-VBOX_HARDDISK_VBe2585d74-5267121b -f
    mkfs.lustre --reformat --failover 10.73.20.22@tcp  --ost --backfstype=zfs --fsname=zfsmo --index=0 --mgsnode=10.73.20.11@tcp oss1/ost00
    zfs compression=on oss1
    mkdir -p /lustre/zfsmo/ost00
    mount -t lustre oss1/ost00 /lustre/zfsmo/ost00

    vagrant ssh oss2
    sudo -s
    zpool create oss2 -o cachefile=none raidz2 /dev/disk/by-id/ata-VBOX_HARDDISK_VBb7776d10-aba16176 /dev/disk/by-id/ata-VBOX_HARDDISK_VB6657241f-bab2ffed  /dev/disk/by-id/ata-VBOX_HARDDISK_VB0ebfc209-9bbf80c4 /dev/disk/by-id/ata-VBOX_HARDDISK_VB51449aa2-95df9cdc -f
    mkfs.lustre --reformat --failover 10.73.20.21@tcp  --ost --backfstype=zfs --fsname=zfsmo --index=1 --mgsnode=10.73.20.11 oss2/ost01
    zfs compression=on oss2
    mkdir -p /lustre/zfsmo/ost01
    mount -t lustre oss2/ost01 /lustre/zfsmo/ost01
```

After all the commands for each had run successfully, use the IML GUI to scan for the filesystem:
    Configuration -> Servers -> Scan for Filesystem.  Use all servers

If Succussfull, in the IML GUI, the filesystem will be available.

## Setting up Clients
In your vagrant folder, run the following script to prepare both client c1 and c2:
```
vagrant sh -c '\
sudo yum-config-manager --add-repo https://copr.fedorainfracloud.org/coprs/managerforlustre/lustre-client/repo/epel-7/managerforlustre-lustre-client-epel-7.repo && \
sudo yum-config-manager --add-repo https://downloads.hpdd.intel.com/public/e2fsprogs/latest/el7/ && \
sudo sed -i -e "1d" -e "2s/^.*$/[e2fsprogs]/" -e "/baseurl/s/,/%2C/g" -e "/enabled/a gpgcheck=0" /etc/yum.repos.d/downloads.hpdd.intel.com_public_e2fsprogs_latest_el7_.repo && \
sudo yum clean metadata && \
sudo yum -y install lustre-client && \
sudo reboot' c1 c2
```
Both clients are now running the lustre-client software and are ready to be mounted. To mount a client, do the following:
1. ssh into the client
```
vagrant ssh c1
```
2. Create a mount directory (it's a good idea to use the same name as the filesystem you created).
```
sudo mkdir -p /mnt/zfsmo
```
3.  Note the NID for the MGS. You can get this by looking at the lustre network interface in the GUI on the server detail page for mds1 or you can run the following command:
```
vagrant ssh mds1
lctl list_nids
# 10.73.20.11@tcp # Notice this is the lustre network interface
```
4. Note the NID for the MDS. You can get this by looking at the lustre network interface in the GUI on the server detail page for mds2 or you can run the following command:
```
vagrant ssh mds2
lctl list_nids
10.73.20.12@tcp # Notice this is the lustre network interface
```
5. Mount the lustre filesystem:
```
sudo mount -t lustre 10.73.20.11@tcp:10.73.20.12@tcp:/fs /mnt/zfsmo
```
6. Use the filesystem. You can test the mount by creating a large file and then checking the results (for testing, it is simplest to use the root account):
```
dd if=/dev/urandom of=/mnt/zfsmo/testfile1.txt bs=1G count=1; cp /mnt/zfsmo/testfile1.txt /mnt/zfsmo/testfile2.txt;
lfs df -h
----------------------------------------------------------------------------
UUID                       bytes        Used   Available Use% Mounted on
fs-MDT0000_UUID             1.7G       25.8M        1.5G   2% /mnt/fs[MDT:0]
fs-OST0000_UUID             2.9G       33.1M        2.6G   1% /mnt/fs[OST:0]
OST0001             : inactive device
fs-OST0002_UUID             2.9G       33.1M        2.6G   1% /mnt/fs[OST:2]
OST0003             : inactive device
fs-OST0004_UUID             2.9G       33.1M        2.6G   1% /mnt/fs[OST:4]
OST0005             : inactive device
fs-OST0006_UUID             2.9G       33.1M        2.6G   1% /mnt/fs[OST:6]
OST0007             : inactive device

filesystem summary:        11.6G      132.6M       10.4G   1% /mnt/fs
```