
from provisioning.models import ChromaManager, ChromaAppliance
from provisioning.lib.chroma_ops import ChromaManagerOps, ChromaApplianceOps

from django.core.management.base import BaseCommand

import time

class Command(BaseCommand):
    args = "[recover]"
    help = "Create a new chroma cluster. "
    can_import_settings = True

    def _create_instances(self):
        manager = ChromaManager.create("chroma")
        ChromaAppliance.create(manager, "node01")
#        ChromaAppliance.create(manager, "node02")
        return manager

    def _setup_instances(self, manager):
        appliances = ChromaAppliance.objects.filter(chroma_manager = manager)
        manager_ops = ChromaManagerOps(manager)

        manager_ops.install_deps()
        manager_ops.setup_chroma()
        manager_ops.create_keys()
        manager_key = manager_ops.get_key()

        for appliance in appliances:
            appliance_ops = ChromaApplianceOps(appliance)
            appliance_ops.set_key(manager_key)
            manager_ops.add_server(appliance_ops)

        time.sleep(30)
        manager_ops.reset_chroma()


    def handle(self, *args, **options):
        if len(args) == 0:
            manager = self._create_instances()
            self._setup_instances(manager)
        elif args[0] == 'recover':
            manager = ChromaManager.objects.get(id = int(args[1]))
            self._setup_instances(manager)

            # TODO: wait for completion of server add and device discovery
            # TODO: once devices are discovered, create a ChromaFilesystem
