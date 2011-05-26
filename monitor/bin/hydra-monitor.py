#!/usr/bin/env python

from django.core.management import setup_environ
import settings
setup_environ(settings)

from monitor.lib.lustre_audit import LustreAudit

from time import sleep
import os

if __name__=='__main__':
    try:
        lustre_audit = LustreAudit()
        while(True):
            lustre_audit.audit_all()
            sleep(5)

    except KeyboardInterrupt:
        print "Exiting..."
        os._exit(0)

