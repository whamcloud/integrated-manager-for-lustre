from optparse import make_option
from provisioning.lib.util import LazyStruct
from provisioning.models import ChromaManager, ChromaAppliance, Node

import settings
from django.core.management.base import BaseCommand, CommandError
from boto.ec2.connection import EC2Connection

from fabric.operations import open_shell

from provisioning.lib.chroma_ops import ChromaManagerOps, ChromaStorageOps


class Command(BaseCommand):
    args = "list | update <id> | add_node <id> | open <id> | ssh <id> | terminate all"
    help = "Utility command to manage instances"
    can_import_settings = True
    option_list = BaseCommand.option_list + (
        make_option("--name", type=str, default="chroma",
            help="name of the new node"),
        make_option("--master", action="store_true",
            help="Update from master repository"),
        make_option("--cluster", "-c",  type=int, default=None,
            help="Update from master repository"),
        make_option("--volumes", type=int, default=4,
            help="number of EBS volumes per OSS"),
        make_option("--recover", type=int, default=0,
            help="Attempt to just perform configuration of nodes")
        )

    def do_list(self):
        for m in ChromaManager.objects.all():
            i = m.node.get_instance()
            print("%s manager %s %s http://%s/" %(m.id, m.node.ec2_id, m.node.name, i.ip_address))
            for a in ChromaAppliance.objects.filter(chroma_manager = m):
                print("    %s %s" % (a.node.name, a.node.ec2_id))

    def handle(self, *args, **options):
        self.options = LazyStruct(**options)
        if not args or args[0] == 'list':
            self.do_list();

        elif args[0] == 'terminate' and len(args) > 1 and args[1] == 'all':
            for a in ChromaAppliance.objects.all():
                appliance_ops = ChromaStorageOps(a)
                appliance_ops.terminate()
            for m in ChromaManager.objects.all():
                manager_ops = ChromaManagerOps(m)
                manager_ops.terminate()

        elif self.options.cluster == None:
            self.do_list()
            raise CommandError('specify a cluster with --cluster <id>')

        elif args[0] == 'terminate':
            manager_id = self.options.cluster
            manager = ChromaManager.objects.get(id = manager_id)
            for appliance in manager.appliances():
                appliance_ops = ChromaStorageOps(appliance)
                appliance_ops.terminate()
            manager_ops = ChromaManagerOps(manager)
            manager_ops.terminate()

        elif args[0] == 'update':
            manager_id = self.options.cluster
            manager = ChromaManager.objects.get(id = manager_id)
            manager_ops = ChromaManagerOps(manager)
            manager_ops.live_update(self.options.master)
            for appliance in manager.appliances():
                appliance_ops = ChromaStorageOps(appliance)
                appliance_ops.live_update(self.options.master)
            manager_ops.reset_chroma()

        elif args[0] == 'add_node':
            manager_id = self.options.cluster
            manager = ChromaManager.objects.get(id = manager_id)
            manager_ops = ChromaManagerOps(manager)
            manager_key = manager_ops.get_key()

            appliance = ChromaAppliance.create(manager, self.options.name)
            appliance_ops = ChromaStorageOps(appliance)
            appliance_ops.configure(self.options.master)
            appliance_ops.configure_oss(self.options.volumes)
            appliance_ops.set_key(manager_key)

            appliances = ChromaAppliance.objects.filter(chroma_manager = manager)
            appliance_ops.add_etc_hosts([manager.node] + [a.node for a in appliances])

            manager_ops.add_etc_hosts([appliance.node])
            manager_ops.add_server(appliance_ops)

        elif args[0] == 'add_client':
            manager_id = self.options.cluster
            name = self.options.name
            manager = ChromaManager.objects.get(id = manager_id)
            manager_ops = ChromaManagerOps(manager)
            manager_key = manager_ops.get_key()

            appliance = ChromaAppliance.create(manager, name)
            appliance_ops = ChromaStorageOps(appliance)
            appliance_ops.set_key(manager_key)
            appliance_ops.configure_client()

            manager_ops.add_etc_hosts([appliance.node])
            appliances = ChromaAppliance.objects.filter(chroma_manager = manager)
            appliance_ops.add_etc_hosts([manager.node] + [a.node for a in appliances])

        elif args[0] == 'open':
            manager_id = self.options.cluster
            manager = ChromaManager.objects.get(id = manager_id)
            from subprocess import call
            url = "http://%s/" % manager.node.get_instance().ip_address
            print "Opening %s..." % url
            call(["open", url])

        elif args[0] == 'ssh':
            manager_id = self.options.cluster
            manager = ChromaManager.objects.get(id = manager_id)
            session = manager.get_session()
            import os
            SSH_BIN = "/usr/bin/ssh"
            os.execvp(SSH_BIN, ["ssh", "-i", settings.AWS_SSH_PRIVATE_KEY, 
                                "%s@%s" % (manager.node.username, session.instance.ip_address)])
