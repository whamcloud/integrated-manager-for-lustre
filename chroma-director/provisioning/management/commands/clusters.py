
from provisioning.models import ChromaManager, ChromaAppliance, Node

import settings
from django.core.management.base import BaseCommand
from boto.ec2.connection import EC2Connection

from fabric.operations import open_shell

from provisioning.lib.chroma_ops import ChromaManagerOps, ChromaApplianceOps


class Command(BaseCommand):
    args = "list|open <id>|ssh <id>|terminate all"
    help = "Utility command to manage instances"
    can_import_settings = True
    def handle(self, *args, **options):
        if not args or args[0] == 'list':
            for m in ChromaManager.objects.all():
                i = m.node.get_instance()
                print("%s manager %s %s http://%s/" %(m.id, m.node.ec2_id, m.node.name, i.ip_address))
                for a in ChromaAppliance.objects.filter(chroma_manager = m):
                    print("    %s %s" % (a.node.name, a.node.ec2_id))

        elif args[0] == 'terminate' and args[1] == 'all':
            for a in ChromaAppliance.objects.all():
                appliance_ops = ChromaApplianceOps(a)
                appliance_ops.terminate()
            for m in ChromaManager.objects.all():
                manager_ops = ChromaManagerOps(m)
                manager_ops.terminate()

        elif args[0] == 'terminate' and int(args[1]) > 0:
            manager_id = int(args[1])
            manager = ChromaManager.objects.get(id = manager_id)
            appliances = ChromaAppliance.objects.filter(chroma_manager = manager)
            for appliance in appliances:
                appliance_ops = ChromaApplianceOps(appliance)
                appliance_ops.terminate()
            manager_ops = ChromaManagerOps(manager)
            manager_ops.terminate()


        elif args[0] == 'add_node':
            manager_id = int(args[1])
            name = args[2]
            manager = ChromaManager.objects.get(id = manager_id)
            manager_ops = ChromaManagerOps(manager)
            manager_key = manager_ops.get_key()

            appliance = ChromaAppliance.create(manager, name)
            appliance_ops = ChromaApplianceOps(appliance)
            appliance_ops.configure()
            appliance_ops.set_key(manager_key)

            appliances = ChromaAppliance.objects.filter(chroma_manager = manager)
            appliance_ops.add_etc_hosts([manager.node] + [a.node for a in appliances])

            manager_ops.add_etc_hosts([appliance.node])
            manager_ops.add_server(appliance_ops)

        elif args[0] == 'open':
            manager_id = int(args[1])
            manager = ChromaManager.objects.get(id = manager_id)
            from subprocess import call
            url = "http://%s/" % manager.node.get_instance().ip_address
            print "Opening %s..." % url
            call(["open", url])

        elif args[0] == 'ssh':
            manager_id = int(args[1])
            manager = ChromaManager.objects.get(id = manager_id)
            session = manager.get_session()
            import os
            SSH_BIN = "/usr/bin/ssh"
            os.execvp(SSH_BIN, ["ssh", "-i", settings.AWS_SSH_PRIVATE_KEY, 
                                "%s@%s" % (manager.node.username, session.instance.ip_address)])

            
                
                
