#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import logging

log = logging.getLogger(__name__)

if not log.handlers:
    handler = logging.FileHandler('cluster_sim.log')
    handler.setFormatter(logging.Formatter("[%(asctime)s: %(levelname)s/%(name)s] %(message)s"))
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)
