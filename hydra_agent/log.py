
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

import logging
import sys

agent_log = logging.getLogger('agent_log')
agent_log.addHandler(logging.StreamHandler(sys.stderr))
agent_log.setLevel(logging.WARNING)
