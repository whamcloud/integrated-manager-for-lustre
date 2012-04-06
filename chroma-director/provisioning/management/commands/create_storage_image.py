
from provisioning.models import Node
from provisioning.lib.chroma_ops import StorageImageOps

from django.core.management.base import BaseCommand
from fabric.operations import run

import settings
import time
import json

class Command(BaseCommand):
    def _create_instances(self):
        node = Node.create(settings.BASE_IMAGE, "storage_image")
        return node

    def _setup_instances(self, node):
        image_ops = StorageImageOps(node)
#        image_ops.install_deps()
        # The first reboot takes a lot longer than subsequent ones, so get it out of the way now
        # (something to do with SElinux rescanning root)
        # However, fabric->ssh  is raising an SSHException('SSH session not active') after the reboot
        # so this is commented out until I can figure out how to avoid that.
        # print "rebooting..."
        # image_ops.reboot()
        # time.sleep(10) # allow reboot to start
        # # Wait until reboot is finshed
        # image_ops.reset_session()
        ami_id = image_ops.make_image("chroma-storage-%s" % time.strftime("%y%m%d"))
        image_ops.terminate()
        config = {
            'username': settings.BASE_IMAGE['username'],
            'ami': ami_id,
            'instance_type': 't1.micro',
            'security_group': 'chroma-appliance'}
        try:
            f = open("local_settings.py", "a")
            f.write("CHROMA_APPLIANCE = %s" % json.dumps(config))
            f.close()
        except:
            print("Please add this to your local_settings.py:")
            print("CHROMA_APPLIANCE = %s" % json.dumps(config))

    def handle(self, *args, **options):
        if len(args) == 0:
            image = self._create_instances()
            self._setup_instances(image)
        elif args[0] == 'recover':
            appliance = Node.objects.get(id = int(args[1]))
            self._setup_instances(appliance)
