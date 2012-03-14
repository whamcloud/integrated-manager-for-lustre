
from provisioning.models import ChromaManager, ChromaAppliance, Ec2Instance

import settings
from django.core.management.base import BaseCommand
from boto.ec2.connection import EC2Connection

class Command(BaseCommand):
    def execute(self, *args, **options):
        if not args or args[0] == 'list':
            for m in ChromaManager.objects.all():
                print m.id, 'manager', m.ec2_instance.ec2_id
            for a in ChromaAppliance.objects.all():
                print a.id, 'appliance', a.ec2_instance.ec2_id

        elif args[0] == 'terminate' and args[1] == 'all':
            conn = EC2Connection(settings.AWS_KEY_ID, settings.AWS_SECRET)
            conn.terminate_instances([i.ec2_id for i in Ec2Instance.objects.all()])
            Ec2Instance.objects.all().delete()

        elif args[0] == 'open':
            manager_id = int(args[1])
            manager = ChromaManager.objects.get(id = manager_id)
            from provisioning.lib.chroma_ops import ChromaManagerOps
            ops = ChromaManagerOps(manager.ec2_instance.ec2_id)
            from subprocess import call
            url = "http://%s/" % ops.ec2_session.instance.ip_address
            print "Opening %s..." % url
            call(["open", url])

        elif args[0] == 'ssh':
            manager_id = int(args[1])
            manager = ChromaManager.objects.get(id = manager_id)
            from provisioning.lib.chroma_ops import ChromaManagerOps
            import os
            ops = ChromaManagerOps(manager.ec2_instance.ec2_id)
            SSH_BIN = "/usr/bin/ssh"
            os.execvp(SSH_BIN, ["ssh", "-i", settings.AWS_SSH_PRIVATE_KEY, "root@%s" % ops.ec2_session.instance.ip_address])

            
                
                
