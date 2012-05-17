import settings

import fabric
import fabric.api
from fabric.operations import sudo, put, get
import StringIO

from provisioning.models import   Node

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
        put(settings.MASTER_REPO, "/etc/yum.repos.d", use_sudo = True)


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
        try:
            instance = self.node.get_instance()
            volumes = [b[1].volume_id for b in instance.block_device_mapping.items() if not b[1].delete_on_termination]
            print "terminating %s %s" % (self.node.name, instance.id)
            instance.terminate()
            if len(volumes):
                self.node.delete_volumes(volumes)
        except:
            print "Unable to terminate node: ", self.node.name, self.node.ec2_id
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
            # XXX !
            sudo('echo "HOSTNAME=%s" >> /etc/sysconfig/network' % self.node.name)
    

class ChromaManagerOps(NodeOps):
    def __init__(self, manager):
        NodeOps.__init__(self, manager.node)
        self.manager = manager

    def terminate(self):
        self.terminate_node()
        self.manager.delete()

    def update_deps(self, use_master):
        with self.open_session():
            self._setup_chroma_repo()
            if use_master:
                sudo('yum --enablerepo=chroma-master -y update')
            else:
                sudo('yum -y update')

    def live_update(self, use_master):
        with self.open_session():
            sudo('chroma-config stop')
        self.update_deps(use_master)

    def setup_chroma(self):
        with self.open_session():
            put("%s" % (settings.CHROMA_SETTINGS), "/usr/share/chroma-manager/local_settings.py", use_sudo = True)
            sudo("chroma-config setup %s %s" % (
                settings.CHROMA_MANAGER_USER,
                settings.CHROMA_MANAGER_PASSWORD))
            sudo("echo '[chroma]' > ~/.chroma")
            sudo("echo username=%s >> ~/.chroma" % settings.CHROMA_MANAGER_USER)
            sudo("echo password=%s >> ~/.chroma" % settings.CHROMA_MANAGER_PASSWORD)

    def reset_chroma(self):
        with self.open_session():
            sudo("chroma-config setup")
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
            sudo("chroma host create --address %s" % appliance_ops.appliance.node.name)

#        from provisioning.lib.chroma_manager_client import AuthorizedHttpRequests
#        manager_url = "http://%s/" % self.session.instance.ip_address
#        appliance_address = "%s@%s" % (settings.CHROMA_APPLIANCE['username'],
#                appliance_ops.session.instance.private_ip_address)
#        requests = AuthorizedHttpRequests(settings.CHROMA_MANAGER_USER, settings.CHROMA_MANAGER_PASSWORD, manager_url)
#        response = requests.post("/api/host/", body = {'address': appliance_address})
#        assert(response.successful)

class ChromaStorageOps(NodeOps):
    def __init__(self, appliance):
        NodeOps.__init__(self, appliance.node)
        self.appliance = appliance

    def terminate(self):
        self.terminate_node()
        self.appliance.delete()

    def update_deps(self, use_master):
        with self.open_session():
            self._setup_chroma_repo()
            # ensure latest version of agent is installed
            # don't do yum update because we don't want to update kernel
            sudo('service chroma-agent stop')
            if use_master:
                sudo('yum --enablerepo=chroma-master install -y chroma-agent-management')
            else:
                sudo('yum install -y chroma-agent-management')
            sudo('service chroma-agent start')

    def live_update(self, use_master):
        self.update_deps(use_master);

    def mkraid(self):
        with self.open_session():
            sudo('mdadm --create /dev/md0 --level 5 -n 4 /dev/xvdj /dev/xvdk /dev/xvdl /dev/xvdm')

    def set_key(self, key):
        with self.open_session():
            sudo("echo \"%s\" >> .ssh/authorized_keys" % key)


    def configure(self, use_master):
        self.set_hostname()
        self.update_deps(use_master)
        with self.open_session():
            sudo("service corosync restart")
            sudo("service rsyslog restart")
            put('../chroma-manager/scripts/loadgen.sh', 'loadgen.sh', mode=0755)

    def configure_oss(self, vol_count):
        self.node.add_volumes(vol_count, 1)

    def configure_mds(self):
        self.node.add_volumes(3, 1)
        #with self.open_session():
        #    sudo('')
        #        self.mkraid()


    def configure_client(self):
        self.set_hostname()
        with self.open_session():
            self._setup_chroma_repo()
            sudo("mkdir /mnt/lustre")
            put('../chroma-manager/scripts/loadgen.sh', 'loadgen.sh', mode=0755)




