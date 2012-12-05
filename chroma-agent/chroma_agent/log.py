#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import logging

# This log is for messages about the internal machinations of our
# daemon and messaging systems, the user would only be interested
# in warnings and errors
daemon_log = logging.getLogger('daemon')

# This log is for messages about operations invoked at the user's request,
# the user will be interested general breezy chat (INFO) about what we're
# doing for them
console_log = logging.getLogger('console')


# Not setting up logs at import time because we want to
# set them up after daemonization
def daemon_log_setup():
    handler = logging.FileHandler("/var/log/chroma-agent.log")
    handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s %(message)s', '%d/%b/%Y:%H:%M:%S'))
    daemon_log.addHandler(handler)


def console_log_setup():
    handler = logging.FileHandler("/var/log/chroma-agent-console.log")
    handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s %(message)s', '%d/%b/%Y:%H:%M:%S'))
    console_log.addHandler(handler)
