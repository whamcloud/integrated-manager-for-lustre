#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


#import socket
#from chroma_agent import shell
#

# FIXME: this appear to be unused
#def verify_corosync():
#    """Verifies the state of corosync"""
#
#    # Is corosync accessible?
#    rc, stdout, stderr = shell.run("crm status", shell=True)
#    if rc != 0:
#        return {'accessible': False,
#                'cluster_member': True,
#                'targets_exist': False
#               }
#
#    # Is this node a member of a cluster?
#    hostname = socket.gethostname()
#    rc, stdout, stderr = shell.run("crm node show %s" % hostname,
#                                       shell=True)
#    if rc != 0 or not "%s: normal" % hostname in stdout:
#        return {'accessible': True,
#                'cluster_member': False,
#                'targets_exist': False
#               }
#
#    # now make sure there are no resources using the Target ocf
#    rc, stdout, stderr = shell.run("crm resource list", shell=True)
#    for line in stdout.split('\n'):
#        if "ocf::chroma:Target" in line:
#            return {'accessible': True,
#                    'cluster_member': True,
#                    'targets_exist': True
#                   }
#
ACTIONS = []
