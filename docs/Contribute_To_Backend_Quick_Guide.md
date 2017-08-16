[**Table of Contents**](index.md)

# Contributing to the IML Backend Quick Guide

## General 
* [How to Contribute to Open Source](https://opensource.guide/how-to-contribute/)

## Prerequisites
* Install an IDE/Editor such as [PyCharm](http://www.jetbrains.com/pycharm/), [VS Code](https://code.visualstudio.com/), [Atom](https://atom.io/) or [Sublime](https://www.sublimetext.com/).
* For this guide, the [VS Code IDE/Editor](https://code.visualstudio.com/Download) has been installed along with the following plugins:
    * Python
    * Python Extended
    * Django Template
    
    ![plugin_python](md_Graphics/plugin_python.png)
    ![plugin_django](md_Graphics/plugin_django.png)
* To modify and test any Backend changes to IML, it will be necessary to install a working version of IML.
    * Create a **Vagrant** virtual cluster outined here: [Install IML on a Vagrant Virtual Cluster](Installing_IML_on_HPC_Storage_Sandbox.md).
    * Edit the **Vagrantfile** to allow for a shared mount. Immediately after the block that states *Create an admin server for the cluster*, add the following line:

        **config.vm.synced_folder ".", "/vagrant", type: "virtualbox"**
    
![shared_mount](md_Graphics/vagrant_shared_mount.png)

This will mount the current local directory to **/vagrant** on the virtual machine.

 * Ensure the ability to log in to the **adm** node as the root user:
    * vagrant up adm
    * vagrant ssh
    * su -
    * ls -al /vagrant
    * The Vagrantfile should be in the directory listing 

## On the Local machine, i.e., not the vagrant virtual machine.

For the desciption that follows, it will be assumed that the Vagrant file and virtual machine information reside in the directory:
``` 
~/vagrant-projects/vhpc 
```
## Contributing to the IML Backend
### Clone the desired Backend repository, for example, the main backend repository:  [intel-manager-for-lustre](https://github.com/intel-hpdd/intel-manager-for-lustre)
```
cd ~/vagrant-projects/vhpc
git clone git@github.com:intel-hpdd/intel-manager-for-lustre.git
```
### Create a branch, always work on a branch.
```
cd intel-manager-for-lustre
git checkout -b  my-fix
```
### Validate that the correct branch has been selected.
```
git branch
```
### Work on the branch.
```
Use VS Code and open ~/vagrant-projects/vhpc/intel-manager-for-lustre
```
## As an Example, make a small python code change.
The code that will be changed will modify the description displayed when rebooting a server.

![server_reboot_1](md_Graphics/server_reboot_1.png)

In VS Code, locate and edit the following file: **host.py**
```
intel-manager-for-lustre 
  > chroma-manager
    > chroma_core
      > models
        > host.py

Search for "Initiate a reboot"
```
On the line containing "Initiate a reboot", add **Hello World**:

Change this line:
```
def description(self):
        return "Initiate a reboot on host %s" % self.host
```
To look like this line:
```
def description(self):
        return "Initiate a Hello World reboot on host %s" % self.host
```
Save the file: **host.py**

## Using the python code change in your cloned repo

### In a seperate terminal, log into the **adm** node
* vagrant ssh adm

Log in as root
* su -

### Stop the IML running services
* chroma-config stop

Go to the cloned **intel-manager-for-lustre** repo on the /vagrant mount point where the code edits were made.
```
cd /vagrant/intel-manager-for-lustre
```
### Generate the files: **host.pyc** and **host.pyo** from the **host.py** file 
```
cd chroma-manager/chroma_core/models
```
Type the command:
* **python -O -m py_compile host.py**

This will create the files: **host.pyc** and **host.pyo**

### Preserve the original files that came with the initial IML install.

```
cd /usr/share/chroma-manager/chroma_core/models

mv host.py host.py-orig
mv host.pyc host.pyc-orig
mv host.pyo host.pyo-orig
```

### Create symbolic links to point to the changes.
```
ln -s /vagrant/intel-manager-for-lustre/chroma-manager/chroma_core/models/host.pyc host.pyc 

ln -s /vagrant/intel-manager-for-lustre/chroma-manager/chroma_core/models/host.pyo host.pyo
```

### Start the IML services
* chroma-config start

## In a browser, go to the IML location
* [https://ct7-adm.lfs.local:8443](https://ct7-adm.lfs.local:8443)

## Verify that the small change worked.

It is possible that the browser cache may require refreshing for the change to take place.

* Click on 
    * Configuration > Servers
    * Select the **Actions** pull-down for one of the Servers in the table.
    * Select the option "Reboot"


![server_actions](md_Graphics/server_actions.png)

* The "Commands" form will pop up.
* Look for your modified message: "Initiate a **Hello World** reboot on host..."

![server_reboot_1](md_Graphics/server_reboot_1.png)


---
# Congratulations! You just made a change to the IML Backend code.
---

## The process outlined above is the basic technique for modifying the Backend IML code.

## A note about starting and stopping chroma-config
* The amount of time to complete 
    * chroma-config start
    * chroma-config stop

* can be time consuming, however, the commands are still an effective way to ensure that all processes start and stop.

* A faster method to restart just the "gunicorn" process can be accomplished as follows:

    * **supervisorctl -c /usr/share/chroma-manager/production_supervisord.conf restart gunicorn**


* To check the IML services status

   * **supervisorctl -c /usr/share/chroma-manager/production_supervisord.conf status**

## Push the code change to github

### On your local machine, i.e., not the vagrant VM:

* cd ~/vagrant-projects/vhpc/intel-manager-for-lustre

Ensure you are on the proper branch
* git branch

Otherwise, change to the **my-fix** branch
* git checkout my-branch

* git status
* git add chroma-manager/chroma_core/models/host.py

* git commit -s 

This will cause tests to run

Add the following comment:

```
This is a test fix for the backend

 - Changed a server description
```

* Save the commit 

## Sync with the github origin

|Git task|Git command|
|--------|--------------|
|  List the Current origin  |  git remote -v |
|  Switch to the master branch |git checkout master |
| Fetch and Rebase | git pull  --rebase |
| Switch back to your branch |  git checkout my-fix |
| Put your changes on top of everyone elses | git rebase master |