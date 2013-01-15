#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from django.core.management import BaseCommand
import settings


class Command(BaseCommand):
    def handle(self, *args, **options):
        from chroma_core.lib.service_config import ServiceConfig

        service_config = ServiceConfig()
        service_config._setup_rabbitmq_credentials()
        service_config._setup_crypto()
        service_config._syncdb()

        print """Great success:
 * run `./manage.py supervisor`
 * open %s""" % settings.SERVER_HTTP_URL
