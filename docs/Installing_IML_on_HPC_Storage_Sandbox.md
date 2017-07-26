[**Intel® Manager for Lustre\* Developer Resources Table of Contents**](index.md)

## Prerequisites:
Please refer to https://github.com/intel-hpdd/vagrantfiles on how to create a virtual HPC storage cluster with vagrant before attempting to install IML.

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
1. Verify the following vagrant plugins are installed:
    ```
    vagrant plugin install vagrant-shell-commander
    ```
2. Obtain the preview 1 build from https://github.com/intel-hpdd/intel-manager-for-lustre/releases/download/4.0.0-preview-1/iml-4.0.0.0.tar.gz
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
4. Exit from the vagrant box and scp the build to the /tmp directory in your admin node. For example, if your admin node is running on port 2200 (you can verify this with `vagrant ssh-config`) and the build is in your Downloads folder:
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
    [user@mini iml]$ scp -F sshcfg ~/Media/iml-4.0.0.0.tar.gz adm:/tmp/.
    iml-4.0.0.0.tar.gz                                                 100%  130MB  69.5MB/s   00:01    
    ```
    This allows you to use the Host name referenced in the ssh config to identify individual nodes in the Vagrant environment, and means you do not have to track the port numbers or use a password. In the above example, the file is copied on to the `adm` VM.
5. ssh into the admin box and install the build:
    ```
    vagrant ssh
    [vagrant@ct7-adm ~]$ sudo su - # (or "sudo -s")
    [vagrant@ct7-adm ~]# cd /tmp
    [vagrant@ct7-adm ~]# tar xvf <buildname>.tar.gz
    [vagrant@ct7-adm ~]# cd <build folder>
    [vagrant@ct7-adm ~]# ./install --no-dbspace-check
    ```
6. Update the /etc/hosts file on your computer to include the following line:
    ```
    127.0.0.1 ct7-adm.lfs.local
    ```
7. Finally, test that a connection can be made to IML by going to the following link in your browser:
https://ct7-adm.lfs.local:8443

## Adding Servers
You should now be able to see IML when navigating to https://ct7-adm.lfs.local:8443. Click on the login link at the top right and log in as the admin. Next, go to the server configuration page and add the following servers:
```
ct7-mds[1,2].lfs.local,ct7-oss[1,2].lfs.local
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
sudo mkdir -p /mnt/fs
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
sudo mount -t lustre 10.73.20.11@tcp:10.73.20.12@tcp:/fs /mnt/fs
```
6. Use the filesystem. You can test the mount by creating a large file and then checking the results (for testing, it is simplest to use the root account):
```
dd if=/dev/urandom of=/mnt/fs/testfile1.txt bs=1G count=1; cp /mnt/fs/testfile1.txt /mnt/fs/testfile2.txt;
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
