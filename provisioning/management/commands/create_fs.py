
from provisioning.models import ChromaManager, ChromaAppliance
from provisioning.lib.chroma_ops import ChromaManagerOps, ChromaApplianceOps

from django.core.management.base import BaseCommand

class Command(BaseCommand):
    def _create_instances(self):
        manager = ChromaManager.create()
        ChromaAppliance.create(manager)
        return manager

    def _setup_instances(self, manager):
        appliances = ChromaAppliance.objects.filter(chroma_manager = manager)
        manager_ops = ChromaManagerOps(manager.ec2_instance.ec2_id)

        manager_ops.install_deps()
        manager_ops.setup_chroma()
        manager_ops.create_keys()
        manager_key = manager_ops.get_key()

        for appliance in appliances:
            appliance_ops = ChromaApplianceOps(appliance.ec2_instance.ec2_id)
            appliance_ops.set_key(manager_key)
            manager_ops.add_server(appliance_ops)


    def execute(self, *args, **options):
        if len(args) == 0:
            manager = self._create_instances()
            self._setup_instances(manager)
        elif args[0] == 'recover':
            manager = ChromaManager.objects.get(id = int(args[1]))
            self._setup_instances(manager)

            # TODO: wait for completion of server add and device discovery
            # TODO: once devices are discovered, create a ChromaFilesystem
