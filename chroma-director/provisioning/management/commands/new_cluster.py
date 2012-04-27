
from optparse import make_option
from django.core.management.base import BaseCommand

from provisioning.models import ChromaManager, ChromaAppliance
from provisioning.lib.chroma_ops import ChromaManagerOps, ChromaStorageOps

import time

class LazyStruct(object):
    """
    It's kind of like a struct, and I'm lazy.
    """
    def __init__(self, **kwargs):
        self.__dict__ = kwargs

    def __getattr__(self, key):
        return self.__dict__[key]


class Command(BaseCommand):
    args = "[recover]"
    help = "Create a new chroma cluster. "
    can_import_settings = True
    option_list = BaseCommand.option_list + (
        make_option("--name", type=str, default="chroma",
            help="name of the cluster"),
        make_option("--oss", type=int, default=1,
            help="number of OSS nodes to create"),
        make_option("--clients", type=int, default=0,
            help="number of client nodes "),
        make_option("--type", type=str, default="t1.micro",
            help="instance type for lustre nodes"),
        make_option("--volumes", type=int, default=4,
            help="number of EBS volumes per OSS")
    )


    def _create_instances(self):
        manager = ChromaManager.create(self.options.name)
        ChromaAppliance.create(manager, "mds1")
        for i in range(0, self.options.oss):
            ChromaAppliance.create(manager, "oss%d" % i)

        return manager


    def _setup_instances(self, manager):
        
        # XXX - using base image instaed of manager AMI
#        self._prepare_image(manager.node)

        appliances = ChromaAppliance.objects.filter(chroma_manager = manager)
        manager_ops = ChromaManagerOps(manager)

        manager_ops.update_deps()
        manager_ops.add_etc_hosts([manager.node] + [a.node for a in appliances])
        manager_ops.set_hostname()
        manager_ops.setup_chroma()
        manager_ops.create_keys()
        manager_key = manager_ops.get_key()

        for appliance in appliances:
            storage_ops = ChromaStorageOps(appliance)
            storage_ops.set_key(manager_key)
            storage_ops.add_etc_hosts([manager.node] + [a.node for a in appliances])
            storage_ops.configure()
            if appliance.node.name == "mds1":
                storage_ops.configure_mds()
            else:
                storage_ops.configure_oss(self.options.volumes)
            manager_ops.add_server(storage_ops)

        print "Chroma is ready! http://%s/" % manager.node.get_instance().ip_address



    def handle(self, *args, **options):
        self.options = LazyStruct(**options)
        if len(args) == 0:
            manager = self._create_instances()
            self._setup_instances(manager)
        elif args[0] == 'recover':
            manager = ChromaManager.objects.get(id = int(args[1]))
            self._setup_instances(manager)


            # TODO: wait for completion of server add and device discovery
            # TODO: once devices are discovered, create a ChromaFilesystem
