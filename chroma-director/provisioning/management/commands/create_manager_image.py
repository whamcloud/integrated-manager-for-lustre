from provisioning.lib.image_ops import ManagerImageOps
from provisioning.models import Node

from django.core.management.base import BaseCommand

import settings
import time
import json

class Command(BaseCommand):
    def _create_instances(self):
        node = Node.create(settings.BASE_IMAGE, "manager_image")
        return node

    def _setup_instances(self, node):
        image_ops = ManagerImageOps(node)
        image_ops.install_deps()
        ami_id = image_ops.make_image("chroma-manager-%s" % time.strftime("%y%m%d"))
        image_ops.terminate()
        config = {
            'username': settings.BASE_IMAGE['username'],
            'ami': ami_id,
            'instance_type': 'm1.small',
            'security_group': 'chroma-manager'}
        try:
            f = open("local_settings.py", "a")
            f.write("CHROMA_MANAGER = %s\n" % json.dumps(config))
            f.close()
        except:
            print("Please add this to your local_settings.py:")
            print("CHROMA_MANAGER = %s" % json.dumps(config))

    def handle(self, *args, **options):
        if len(args) == 0:
            image = self._create_instances()
            self._setup_instances(image)
        elif args[0] == 'recover':
            appliance = Node.objects.get(id = int(args[1]))
            self._setup_instances(appliance)
