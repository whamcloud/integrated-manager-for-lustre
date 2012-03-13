from django.db import models

import settings

from boto.ec2.connection import EC2Connection

class Ec2Instance(models.Model):
    ec2_id = models.CharField(max_length = 10, unique = True)

    @classmethod
    def create(cls, instance_settings):
        conn = EC2Connection(settings.AWS_KEY_ID, settings.AWS_SECRET)

        reservation = conn.run_instances(
                instance_settings['ami'],
                key_name = settings.AWS_SSH_KEY,
                instance_type = instance_settings['instance_type'],
                security_groups = [instance_settings['security_group']])

        instance = reservation.instances[0]

        obj = Ec2Instance(ec2_id = instance.id)
        obj.save()
        return obj

class ChromaManager(models.Model):
    ec2_instance = models.ForeignKey(Ec2Instance, unique = True)

    @classmethod
    def create(cls):
        ec2_instance = Ec2Instance.create(settings.CHROMA_MANAGER)
        obj = ChromaManager(ec2_instance = ec2_instance)
        obj.save()
        return obj

class ChromaAppliance(models.Model):
    ec2_instance = models.ForeignKey(Ec2Instance, unique = True)

    chroma_manager = models.ForeignKey(ChromaManager)

    @classmethod
    def create(cls, manager):
        ec2_instance = Ec2Instance.create(settings.CHROMA_APPLIANCE)
        obj = ChromaAppliance(ec2_instance = ec2_instance, chroma_manager = manager)
        obj.save()
        return obj

class ChromaFilesystem(models.Model):
    name = models.CharField(max_length = 8)
    chroma_manager = models.ForeignKey(ChromaManager)
    chroma_id = models.IntegerField()

# Create your models here.
