
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
                print m.id, 'manager', m.node.ec2_id, m.node.name
            for a in ChromaAppliance.objects.all():
                i = a.node.get_instance()
                print a.id, 'appliance', a.node.ec2_id, a.node.name, i.state, i.ip_address

        elif args[0] == 'terminate' and args[1] == 'all':
            for a in ChromaAppliance.objects.all():
                appliance_ops = ChromaApplianceOps(a)
                appliance_ops.terminate()
            for m in ChromaManager.objects.all():
                manager_ops = ChromaManagerOps(m)
                manager_ops.terminate()
#            conn = EC2Connection(settings.AWS_KEY_ID, settings.AWS_SECRET)
#            conn.terminate_instances([i.ec2_id for i in Node.objects.all()])
#            Node.objects.all().delete()

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

            
                
                
