from optparse import make_option

from provisioning.lib.image_ops import ManagerImageOps, StorageImageOps
from provisioning.models import Node
from provisioning.lib.util import LazyStruct

from django.core.management.base import BaseCommand

import settings
import time
import json

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option("--name", type=str,
            default =  "chroma-manager-%s" % time.strftime("%y%m%d"),
            help="name of the new image"),
        make_option("--type", choices = ["manager", "storage"],
            help = "manager or storage instance"),
        make_option("--recover", action="store_true",
            help = "attempt to resume image preparation")
    )
    def _create_instances(self):
        node = Node.create(settings.BASE_IMAGE, self.options.name)
        return node

    def prepare_manager_image(self, node):
        image_ops = ManagerImageOps(node)
        image_ops.install_deps()
        ami_id = image_ops.make_image(self.options.name)
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

    def prepare_storage_image(self, node):
        image_ops = StorageImageOps(node)
        image_ops.install_deps()
        # The first reboot takes a lot longer than subsequent ones, so get it out of the way now
        # (something to do with SElinux rescanning root)
        # However, fabric->ssh  is raising an SSHException('SSH session not active') after the reboot
        # so this is commented out until I can figure out how to avoid that.
        # print "rebooting..."
        # image_ops.reboot()
        # time.sleep(10) # allow reboot to start
        # # Wait until reboot is finshed
        # image_ops.reset_session()
        ami_id = image_ops.make_image(self.options.name)
        image_ops.terminate()
        config = {
            'username': settings.BASE_IMAGE['username'],
            'ami': ami_id,
            'instance_type': 't1.micro',
            'security_group': 'chroma-appliance'}
        try:
            f = open("local_settings.py", "a")
            f.write("CHROMA_APPLIANCE = %s\n" % json.dumps(config))
            f.close()
        except:
            print("Please add this to your local_settings.py:")
            print("CHROMA_APPLIANCE = %s" % json.dumps(config))


    def handle(self, *args, **options):
        self.options = LazyStruct(**options)
        if not self.options.recover:
            image = self._create_instances()
        else:
            image = Node.objects.get(id = int(args[0]))

        if self.options.type == "manager":
            self.prepare_manager_image(image)
        else:
            self.prepare_storage_image(image)
