#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import logging
import sys

agent_log = logging.getLogger('agent_log')
agent_log.addHandler(logging.StreamHandler(sys.stderr))
agent_log.setLevel(logging.WARNING)
