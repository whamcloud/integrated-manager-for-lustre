
from provisioning.models import Node
from provisioning.lib.chroma_ops import StorageImageOps

from django.core.management.base import BaseCommand

import settings
from boto.ec2.connection import EC2Connection

class Command(BaseCommand):
    def _create_instances(self):
        node = Node.create(settings.BASE_IMAGE, "image_node")
        return node

    def _setup_instances(self, node):
        image_ops = StorageImageOps(node)
        image_ops.install_deps()

    def execute(self, *args, **options):
        if len(args) == 0:
            image = self._create_instances()
            self._setup_instances(image)
        elif args[0] == 'recover':
            appliance = Node.objects.get(id = int(args[1]))
            self._setup_instances(appliance)
