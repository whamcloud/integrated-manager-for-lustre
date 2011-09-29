#!/usr/bin/env python
#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from distutils.core import setup
from hydra_agent import __version__

setup(
    name = 'hydra-agent',
    version = __version__,
    author = "Whamcloud, Inc.",
    author_email = "info@whamcloud.com",
    packages = ['hydra_agent', 'hydra_agent/actions', 'hydra_agent/cmds', 'hydra_agent/audit', 'hydra_agent/audit/lustre'],
    scripts = ['bin/hydra-agent.py'],
    data_files=[('/usr/lib/ocf/resource.d/hydra', ['Target'])],
    url = 'http://www.whamcloud.com/',
    license = 'Proprietary',
    description = 'The Whamcloud Lustre Monitoring and Adminisration Interface Agent', 
    long_description = open('README.txt').read(),
)
