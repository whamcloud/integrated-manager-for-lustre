# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import logging

log = logging.getLogger(__name__)

if not log.handlers:
    handler = logging.FileHandler('cluster_sim.log')
    handler.setFormatter(logging.Formatter("[%(asctime)s: %(levelname)s/%(name)s] %(message)s"))
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)
