import time
from boto.ec2 import EC2Connection
from fabric.operations import sudo, put, run
from provisioning.lib.chroma_ops import NodeOps
import settings

__author__ = 'rread'

#
# Classes to Create AMIs
#

class ImageOps(NodeOps):
    def _clean_image(self):
        with self.open_session():
            sudo('rm -f ~/.bash_history')
            sudo('rm -f /var/log/secure')
            sudo('rm -f /var/log/lastlog')
            sudo('rm -rf /root/*')
            sudo('rm -rf /tmp/*')
            sudo('rm -rf /root/.*hist*')
            sudo('rm -rf /var/log/*.gz')
            sudo('rm -f /etc/ssh/ssh_host*')
            sudo('rm -f /etc/yum.repos.d/chroma*.repo*')
            sudo('find /home -maxdepth 1 -type d -exec rm -rf {}/.ssh \;')


    def make_image(self, image_name):
        self._clean_image()
        conn = EC2Connection(settings.AWS_KEY_ID, settings.AWS_SECRET)
        image_id = conn.create_image(self.node.ec2_id, image_name)
        time.sleep(5)
        image = conn.get_image(image_id=image_id)

        print "waiting for image (%s) to finish... (can take a very long time)" % image.id
        while(image.state == u'pending'):
            time.sleep(10)
            image = conn.get_image(image_id=image_id)
        print "New AMI is %s  %s" % (image.id, image.state)
        return image.id

    def _update_whamos(self, use_master):
        sudo('yum -y remove cups') # XXX base image specific
        sudo('userdel -r vishal') # XXX base image specific
        if use_master:
            sudo('yum --enablerepo=chroma-master --enablerepo=coeus-master -y update')
        else:
            sudo('yum -y update')


class StorageImageOps(ImageOps):
    # n.b. unlike a manager, a new storage image must be rebooted before it can used
    def install_deps(self, use_master):
        with self.open_session():
            self._setup_chroma_repo()
            self._update_whamos(use_master)
            sudo('yum install -y ntp')
            if use_master:
                sudo('rpm -ivh http://download.fedoraproject.org/pub/epel/6/i386/epel-release-6-7.noarch.rpm')
                sudo('yum --enablerepo=coeus-master install -y lustre kernel-2.6.32*lustre.*')
            else:
                sudo('yum install -y lustre')
            sudo('grubby --set-default "/boot/vmlinuz-2.6.32-*lustre*"')
            if use_master:
                sudo('yum --enablerepo=chroma-master install -y chroma-agent-management')
            else:
                sudo('yum install -y chroma-agent-management')
            put("%s" % (settings.COROSYNC_CONF), "/etc/corosync/corosync.conf", use_sudo = True)
            put("%s" % (settings.COROSYNC_INIT), "/etc/init.d/corosync", use_sudo = True, mode=0755)
            sudo("service corosync start")
            time.sleep(30) # should wait for crm status to be ONLINE
            sudo('crm_attribute --attr-name no-quorum-policy --attr-value ignore')
            sudo('crm configure property stonith-enabled=false')
            sudo('crm configure property symmetric-cluster=false')


class ManagerImageOps(ImageOps):
    def install_deps(self, use_master):
        with self.open_session():
            self._setup_chroma_repo()
            self._update_whamos(use_master)
            #run('wget http://download.fedoraproject.org/pub/epel/6/i386/epel-release-6-6.noarch.rpm')
            #sudo('rpm -i --force epel-release-6-6.noarch.rpm')
            if use_master:
                sudo('rpm -ivh http://download.fedoraproject.org/pub/epel/6/i386/epel-release-6-7.noarch.rpm')
                sudo('yum install --enablerepo=chroma-master --enablerepo=coeus-master -y chroma-manager chroma-manager-cli')
            else:
                sudo('yum install -y chroma-manager chroma-manager-cli')
