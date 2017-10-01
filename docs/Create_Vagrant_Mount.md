[**Table of Contents**](index.md)

# Create a Vagrant Shared Mount from the guest machine to the vagrant virtual machine


* Edit the **Vagrantfile** to allow for a shared mount. Immediately after the block that states *Create an admin server for the cluster*, add the following line:

    **config.vm.synced_folder ".", "/vagrant", type: "virtualbox"**
    
* The first parameter is a path to a directory on the host machine. If the path is relative, it is relative to the project root. The second parameter must be an absolute path of where to share the folder within the guest machine. This folder will be created (recursively, if it must) if it does not exist. See: [synced folder help](https://www.vagrantup.com/docs/synced-folders/basic_usage.html) for more information.
    

![shared_mount](md_Graphics/vagrant_shared_mount.png)

This will mount the current local directory to **/vagrant** on the virtual machine.

 * Ensure the ability to log in to the **adm** node as the root user:
    * vagrant up adm
    * vagrant ssh
    * su -i
    * ls -al /vagrant
    * The Vagrantfile should be in the directory listing 