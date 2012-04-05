
from provisioning.models import ChromaManager, ChromaAppliance
from provisioning.lib.chroma_ops import ChromaManagerOps, ChromaApplianceOps

from django.core.management.base import BaseCommand

import settings
from boto.ec2.connection import EC2Connection

class Command(BaseCommand):
    def _create_instances(self):
        manager = ChromaManager.create()
        return manager

    def _setup_instances(self, appliance):
        appliance_ops = ChromaManagerOps(appliance.ec2_instance.ec2_id)
        appliance_ops.install_app_deps()
        conn = EC2Connection(settings.AWS_KEY_ID, settings.AWS_SECRET)
        conn.reboot_instances([appliance.ec2_instance.ec2_id])


    def execute(self, *args, **options):
        if len(args) == 0:
            appliance = self._create_instances()
            self._setup_instances(appliance)
        elif args[0] == 'recover':
            appliance = ChromaManager.objects.get(id = int(args[1]))
            self._setup_instances(appliance)

            # TODO: wait for completion of server add and device discovery
            # TODO: once devices are discovered, create a ChromaFilesystem
