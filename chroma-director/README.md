# Chroma Director Prototype #

**This is a prototype intended for experimentation and testing!**

**The SSH package we're using current, fabric, does not support SOCKS proxies.  Currently you need to drop off the VPN to get this to work.**

## Prepare environment ##

First, create a local_settings.py with your AWS info:

    AWS_KEY_ID='' # From your 'security credentials -> access keys' page
    AWS_SECRET='' # From your 'security credentials -> access keys' page
    AWS_SSH_KEY = 'jcs-aws-key' # An AWS keypair name
    AWS_SSH_PRIVATE_KEY = '/Users/jcspray/ec2/jcs-aws-key.pem' # a local path

make sure you have the required two security groups in your AWS account:
chroma-manager (ports 22, 80, 514)
chroma-appliance  (port 22, 988)

create a virtualenv and do a 

    pip install -r requirements.txt

Setup the database:
 
    ./manage.py syncdb --migrate --noinput

## Create Base Images (AMIs) ##

Create AMIs from the manager and storage instances.  Each of these
will take several minutes.

    ./manage.py create_image --type manager
    ./manage.py create_image --type storage

Both of these commands are unusual in that they don't save their local
state in the database. They each append he appropriate config statement to
local-settings.py.  This makes it easier to tweak the settings -
particularly useful if you want to change the instance type. 

## Create and manage Chroma clusters ##


Create one manager, one MDS node, and 4 OSS nodes with 4 EBS volumes each using the latest build of the master branch.  This treats the manager instance as the cluster head node, and, for example, creates host aliases for all the oss and mds nodes on the manager node. 

    manage.py new_cluster  --name test --oss 4 --volumes 4 --master

Get a list of your instances with their local cluster IDs.  

    ./manage.py clusters

When some instances have been created, try to set them up again e.g. if something
 went wrong and you've fixed it now. 

    ./manage.py new_cluster recover -c <id>

Remove all the locally-known instances (i.e. those created with director).

    ./manage.py clusters terminate all

Remove the manager and associated storage nodes. 

    ./manage.py clusters terminate -c <id>

Remove all the locally-known instances, i.e. those created with director.

    ./manage.py clusters terminate all

Open an ssh session to a ChromaManager by its local ID.

    ./manage.py clusters ssh -c <id>

## Manage individual nodes ##

Occasionally a node is orphaned and not associated with a particular cluster. Also, these commands are useful if you want to ssh directly to a particular node, instead of going throughout the cluster head node.

List all locally created instances, with IDs, state, IP address, etc.

    ./manage.py nodes

Open ssh connection to instance

    ./manage.py nodes ssh <id>

Destroy specified instance and all attached EBS storage. 

    ./manage.py nodes terminate <id>

Terminate all nodes

    ./manage.py nodes terminate all

Create a new  AMI based on the specified instance

    ./manage.py new_image <id> <name>


Notes:

* aliases are assigned to the instances, and /etc/hosts is updated on
  all the nodes.  The manager is called "chroma" and the storage nodes are called
  node01, node02, etc.
