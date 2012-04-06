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

        print "terminating %s %s" % (self.node.name, instance.id)
        instance.terminate()
        self.node.delete()

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
    

class ChromaManagerOps(NodeOps):
    def __init__(self, manager):
        NodeOps.__init__(self, manager.node)
        self.manager = manager

    def terminate(self):
        self.terminate_node()
        self.manager.delete()

    def update_deps(self):
        with self.open_session():
            sudo('yum install -y hydra-server hydra-server-cli')

    def setup_chroma(self):
        with self.open_session():
            sudo("chroma-config setup %s %s" % (
                settings.CHROMA_MANAGER_USER,
                settings.CHROMA_MANAGER_PASSWORD))

    def reset_chroma(self):
        with self.open_session():
            sudo("chroma-config start")

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
            # ensure latest version of agent is installed
            sudo('yum install -y hydra-agent-management')
        
    def add_volume(self, size, device):
        instance = self.appliance.node.get_instance()
        conn = EC2Connection(settings.AWS_KEY_ID, settings.AWS_SECRET)
        vol = conn.create_volume(size, instance.placement)
        vol.attach(instance.id, device)


    def set_key(self, key):
        with self.open_session():
            sudo("echo \"%s\" >> .ssh/authorized_keys" % key)

    def reset_corosync(self):
        with self.open_session():
            sudo("service corosync restart")

#
# Classes to Create AMIs
#
class ImageOps(NodeOps):
    def _setup_chroma_repo(self):
        sudo('mkdir -p /root/keys')
        for key in ['chroma_ca-cacert.pem', 'privkey-nopass.pem', 'test-ami-cert.pem']:
            put("%s/%s" % (settings.YUM_KEYS, key), "/root/keys/%s" % key, use_sudo = True)
        put(settings.YUM_REPO, "/etc/yum.repos.d", use_sudo = True)

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
            sudo('find /home -maxdepth 1 -type d -exec rm -rf {}/.ssh \;')
        

    def make_image(self, image_name):
        self._clean_image()
        conn = EC2Connection(settings.AWS_KEY_ID, settings.AWS_SECRET)
        image_id = conn.create_image(self.node.ec2_id, image_name)
        image = conn.get_image(image_id=image_id)

        print "waiting for image to finish... (can take a very long time)"
        while(image.state == u'pending'):
            time.sleep(10)
            image = conn.get_image(image_id=image_id)
        print "New AMI is %s  %s" % (image.id, image.state)
        return image.id


class StorageImageOps(ImageOps):
    # n.b. unlike a manager, a new storage image must be rebooted before it can used
    def install_deps(self):
        with self.open_session():
            self._setup_chroma_repo()
            sudo('yum install -y lustre')
            sudo('grubby --set-default "/boot/vmlinuz-2.6.32-*lustre*"')
            sudo('yum install -y hydra-agent-management')
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
            run('wget http://download.fedoraproject.org/pub/epel/6/i386/epel-release-6-5.noarch.rpm')
            sudo('rpm -i --force epel-release-6-5.noarch.rpm')
            self._setup_chroma_repo()
            sudo('yum install -y Django-south hydra-server hydra-server-cli')
