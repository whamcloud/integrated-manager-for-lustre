import settings

from boto.ec2.connection import EC2Connection
import fabric
import fabric.api
from fabric.operations import sudo, run, put, get
from fabric.exceptions import NetworkError
import StringIO
import time

from provisioning.models import ChromaManager, ChromaAppliance, Node

class NodeOps(object):
    def __init__(self, node):
        self.node = node
        self.session = None
        
    @classmethod
    def get(cls, node_id):
        node = Node.objects.get(id = node_id)
        return NodeOps(node)


    def _setup_chroma_repo(self):
        sudo('mkdir -p /root/keys')
        for key in ['chroma_ca-cacert.pem', 'privkey-nopass.pem', 'test-ami-cert.pem']:
            put("%s/%s" % (settings.YUM_KEYS, key), "/root/keys/%s" % key, use_sudo = True)
        put(settings.YUM_REPO, "/etc/yum.repos.d", use_sudo = True)


    def reboot(self):
        instance = self.node.get_instance()
        instance.reboot()
        

    def open_session(self):
        if self.session is None:
            self.session = self.node.get_session()
        return self.session.fabric_settings()

    def reset_session(self):
        self.session = self.node.get_session()

    def terminate_node(self):
        instance = self.node.get_instance()
        volumes = [b[1].volume_id for b in instance.block_device_mapping.items() if not b[1].delete_on_termination]
        print "terminating %s %s" % (self.node.name, instance.id)
        instance.terminate()
        if len(volumes):
            print "need to delete", volumes
            conn = EC2Connection(settings.AWS_KEY_ID, settings.AWS_SECRET)
            for vol in conn.get_all_volumes(volumes):
                if vol.status != u'available':
                    print "detaching volume: %s  %s" % (vol.id, vol.status)
                    vol.detach(force=True)

            detaching = 1
            while detaching:
                detaching = 0
                for vol in conn.get_all_volumes(volumes):
                    detaching += vol.status != u'available'
                time.sleep(10)

            for vol in conn.get_all_volumes(volumes):
                print "deleting volume: %s  %s" % (vol.id, vol.status)
                vol.delete()

        self.node.delete()

    def add_volume(self, size, device):
        instance = self.node.get_instance()
        conn = EC2Connection(settings.AWS_KEY_ID, settings.AWS_SECRET)
        vol = conn.create_volume(size, instance.placement)
        vol.attach(instance.id, device)
        while vol.status != u'in-use':
            print("waiting for volume %s %s" % (vol.id, vol.status))
            time.sleep(10)
            vol = conn.get_all_volumes([vol.id])[0]
        print("Attached volume %s" % (vol.id))
        
    def terminate(self):
        self.terminate_node()

    def add_etc_hosts(self, nodes):
        with self.open_session():
            for node in nodes:
                i = node.get_instance()
                sudo("echo \"%s %s\" >> /etc/hosts" % (i.private_ip_address, node.name))

    def set_hostname(self):
        with self.open_session():
            sudo("hostname %s" %(self.node.name))
            # XXX !
            sudo('echo "HOSTNAME=%s" >> /etc/sysconfig/network' % self.node.name)
    

class ChromaManagerOps(NodeOps):
    def __init__(self, manager):
        NodeOps.__init__(self, manager.node)
        self.manager = manager

    def terminate(self):
        self.terminate_node()
        self.manager.delete()

    def update_deps(self):
        with self.open_session():
            self._setup_chroma_repo()
            sudo('yum -y update')

    def setup_chroma(self):
        with self.open_session():
            put("%s" % (settings.CHROMA_SETTINGS), "/usr/share/chroma-manager/local_settings.py", use_sudo = True)
            sudo("chroma-config setup %s %s" % (
                settings.CHROMA_MANAGER_USER,
                settings.CHROMA_MANAGER_PASSWORD))

    def reset_chroma(self):
        with self.open_session():
            sudo("chroma-config start")
            sudo("service httpd restart")

    def create_keys(self):
        with self.open_session():
            with fabric.api.settings(warn_only = True):
                result = get(".ssh/id_rsa.pub", open("/dev/null", 'w'))
            if result.failed:
                sudo('ssh-keygen -t rsa -N "" -f .ssh/id_rsa')

    def get_key(self):
        buf = StringIO.StringIO()
        with self.open_session():
            get(".ssh/id_rsa.pub", buf)
        return buf.getvalue()

    def add_server(self, appliance_ops):
        with self.open_session():
            sudo("chroma --username %s --password %s host create --address %s" % (
                    settings.CHROMA_MANAGER_USER,
                    settings.CHROMA_MANAGER_PASSWORD,
                    appliance_ops.appliance.node.name))

#        from provisioning.lib.chroma_manager_client import AuthorizedHttpRequests
#        manager_url = "http://%s/" % self.session.instance.ip_address
#        appliance_address = "%s@%s" % (settings.CHROMA_APPLIANCE['username'],
#                appliance_ops.session.instance.private_ip_address)
#        requests = AuthorizedHttpRequests(settings.CHROMA_MANAGER_USER, settings.CHROMA_MANAGER_PASSWORD, manager_url)
#        response = requests.post("/api/host/", body = {'address': appliance_address})
#        assert(response.successful)

class ChromaApplianceOps(NodeOps):
    def __init__(self, appliance):
        NodeOps.__init__(self, appliance.node)
        self.appliance = appliance

    def terminate(self):
        self.terminate_node()
        self.appliance.delete()

    def update_deps(self):
        with self.open_session():
            self._setup_chroma_repo()
            # ensure latest version of agent is installed
            # don't do yum update because we don't want to update kernel
            sudo('yum install -y chroma-agent-management')
        
    def mkraid(self):
        with self.open_session():
            sudo('mdadm --create /dev/md0 --level 5 -n 4 /dev/xvdj /dev/xvdk /dev/xvdl /dev/xvdm')

    def set_key(self, key):
        with self.open_session():
            sudo("echo \"%s\" >> .ssh/authorized_keys" % key)

    def reset_corosync(self):
        with self.open_session():
            sudo("service corosync restart")

    def configure(self):
        self.set_hostname()
        self.update_deps()
        self.add_volume(1, 'sdf')
        self.add_volume(1, 'sdg')
        self.add_volume(1, 'sdh')
        self.add_volume(1, 'sdi')
#        self.mkraid()
        self.reset_corosync()
        with self.open_session():
            put('../chroma-manager/scripts/loadgen.sh', 'loadgen.sh', mode=0755)


    def configure_client(self):
        self.set_hostname()
        with self.open_session():
            self._setup_chroma_repo()
            sudo("mkdir /mnt/lustre")
            put('../chroma-manager/scripts/loadgen.sh', 'loadgen.sh', mode=0755)


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
            sudo('rm -f /etc/yum.repos.d/chroma.repo')
            sudo('find /home -maxdepth 1 -type d -exec rm -rf {}/.ssh \;')
        

    def make_image(self, image_name):
        self._clean_image()
        conn = EC2Connection(settings.AWS_KEY_ID, settings.AWS_SECRET)
        image_id = conn.create_image(self.node.ec2_id, image_name)
        image = conn.get_image(image_id=image_id)

        print "waiting for image (%s) to finish... (can take a very long time)" % image.id
        while(image.state == u'pending'):
            time.sleep(10)
            image = conn.get_image(image_id=image_id)
        print "New AMI is %s  %s" % (image.id, image.state)
        return image.id

    def _update_whamos(self):
        sudo('yum install -y whamos-release')
        # Disable the repo file added by whamos-release
        put(settings.WHAMOS_REPO, "/etc/yum.repos.d", use_sudo = True)
        sudo('yum -y remove cups') # XXX base image specific
        sudo('userdel -r vishal') # XXX base image specific
        sudo('yum -y update')


class StorageImageOps(ImageOps):
    # n.b. unlike a manager, a new storage image must be rebooted before it can used
    def install_deps(self):
        with self.open_session():
            self._setup_chroma_repo()
            self._update_whamos()
            sudo('yum install -y kernel')
            sudo('yum install -y lustre')
            sudo('grubby --set-default "/boot/vmlinuz-2.6.32-*lustre*"')
            sudo('yum install -y chroma-agent-management')
            put("%s" % (settings.COROSYNC_CONF), "/etc/corosync/corosync.conf", use_sudo = True)
            put("%s" % (settings.COROSYNC_INIT), "/etc/init.d/corosync", use_sudo = True, mode=0755)
            sudo("service corosync start")
            time.sleep(30) # should wait for crm status to be ONLINE
            sudo('crm_attribute --attr-name no-quorum-policy --attr-value ignore')
            sudo('crm configure property stonith-enabled=false')
            sudo('crm configure property symmetric-cluster=false')


class ManagerImageOps(ImageOps):
    def install_deps(self):
        with self.open_session():
            self._setup_chroma_repo()
            self._update_whamos()
            run('wget http://download.fedoraproject.org/pub/epel/6/i386/epel-release-6-5.noarch.rpm')
            sudo('rpm -i --force epel-release-6-5.noarch.rpm')
            sudo('yum install -y Django-south chroma-manager chroma-manager-cli')
