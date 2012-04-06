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

        obj = Node(ec2_id = instance.id, username=instance_settings['username'],  name = name) 
        obj.save()
        return obj

    def get_instance(self):
        conn = EC2Connection(settings.AWS_KEY_ID, settings.AWS_SECRET)
        reservations = conn.get_all_instances([self.ec2_id])
        assert(len(reservations) == 1)
        return  reservations[0].instances[0]

    def get_session(self):
        return NodeSession(self)


    def reboot(self):
        conn = EC2Connection(settings.AWS_KEY_ID, settings.AWS_SECRET)
        conn.reboot_instances(instance_ids=[self.ec2_id])

# class Volume(models.Model):
#     ebs_id = models.CharField(max_length = 10, unique = True)
#     node = models.ForeignKey(Node)

#     @classmethod
#     def create(cls, size, node):
#         instance = node.get_instance()
#         conn = EC2Conection(settings.AWS_KEY_ID, settings.AWS_SECRET)
#         conn.create_volume(size,instance.placement)

#         obj = Volume(ebs_id = id, size = size, node = node)
#         obj.save()
        # return obj

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
