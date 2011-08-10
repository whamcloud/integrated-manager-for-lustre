#!/usr/bin/env python

from distutils.core import setup
from hydra_agent import __version__

setup(
    name = 'hydra-agent',
    version = __version__,
    author = "Whamcloud, Inc.",
    author_email = "info@whamcloud.com",
    packages = ['hydra_agent', 'hydra_agent/cmds'],
    scripts = ['bin/hydra-agent.py', 'bin/hydra-rmmod.py'],
    url = 'http://www.whamcloud.com/',
    license = 'Proprietary',
    description = 'The Whamcloud Lustre Monitoring and Adminisration Interface Agent', 
    long_description = open('README.txt').read(),
)
