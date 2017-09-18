[**Table of Contents**](index.md)

# Setting up IML Clients

In your vagrant folder, run the following script to prepare both client c1 and c2:
```
vagrant sh -c '\
sudo yum-config-manager --add-repo https://build.whamcloud.com/lustre-b2_10_last_successful_client/ && \
sudo yum -y install lustre-client && \
' c1 c2
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
10.73.20.11@tcp   <--  Notice this is the lustre network interface
```
4. Note the NID for the MDS. You can get this by looking at the lustre network interface in the GUI on the server detail page for mds2 or you can run the following command:
```
vagrant ssh mds2
lctl list_nids
10.73.20.12@tcp   <--  Notice this is the lustre network interface
```
5. Mount the lustre filesystem:
```
sudo mount -t lustre 10.73.20.11@tcp:10.73.20.12@tcp:/fs /mnt/fs

--OR--

sudo mount -t lustre mds1@tcp:mds2@tcp:/fs /mnt/fs
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