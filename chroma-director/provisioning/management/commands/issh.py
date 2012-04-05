#!/usr/bin/env python

import os

from django.conf import settings
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    def execute(self, *args, **options):
        from boto.ec2.connection import EC2Connection
        ec2_id = args[0]
        conn = EC2Connection(settings.AWS_KEY_ID, settings.AWS_SECRET)
        reservations = conn.get_all_instances([ec2_id])
        assert(len(reservations) == 1)
        instance = reservations[0].instances[0]

        SSH_BIN = "/usr/bin/ssh"
        os.execvp(SSH_BIN, ["ssh", "-i", settings.AWS_SSH_PRIVATE_KEY, "root@%s" % instance.ip_address])
