from django.db import models

import settings

from boto.ec2.connection import EC2Connection
from provisioning.lib.node_session import NodeSession

class Node(models.Model):
    ec2_id = models.CharField(max_length = 10, unique = True)
    username = models.CharField(max_length = 25, default = "root")
    name = models.CharField(max_length = 20)

    @classmethod
    def create(cls, instance_settings, name):
        conn = EC2Connection(settings.AWS_KEY_ID, settings.AWS_SECRET)

        reservation = conn.run_instances(
                instance_settings['ami'],
                key_name = settings.AWS_SSH_KEY,
                instance_type = instance_settings['instance_type'],
                security_groups = [instance_settings['security_group']])

        instance = reservation.instances[0]

        obj = Node(ec2_id = instance.id, username=instance_settings['username'], name = name)
        obj.save()
        return obj

    def get_session(self):
        return NodeSession(self)


class ChromaManager(models.Model):
    node = models.ForeignKey(Node, unique = True, null = True)

    @classmethod
    def create(cls, name):
        node = Node.create(settings.CHROMA_MANAGER, name)
        obj = ChromaManager(node = node)
        obj.save()
        return obj

    def get_session(self):
        return self.node.get_session()


class ChromaAppliance(models.Model):
    node = models.ForeignKey(Node, unique = True, null = True)
    chroma_manager = models.ForeignKey(ChromaManager)

    @classmethod
    def create(cls, manager, name):
        node = Node.create(settings.CHROMA_APPLIANCE, name)
        obj = ChromaAppliance(node = node, chroma_manager = manager)
        obj.save()
        return obj

    def get_session(self):
        return self.node.get_session()
    
class ChromaFilesystem(models.Model):
    name = models.CharField(max_length = 8)
    chroma_manager = models.ForeignKey(ChromaManager)
    chroma_id = models.IntegerField()

# Create your models here.
