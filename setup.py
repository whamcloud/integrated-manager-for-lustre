#!/usr/bin/env python
#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from setuptools import setup, find_packages
from hydra_agent import __version__

excludes = ["*.tests", "*.tests.*", "tests.*", "tests"]

setup(
    name = 'hydra-agent',
    version = __version__,
    author = "Whamcloud, Inc.",
    author_email = "info@whamcloud.com",
    url = 'http://www.whamcloud.com/',
    packages = find_packages(exclude=excludes),
    data_files=[('/usr/lib/ocf/resource.d/hydra', ['Target'])],
    license = 'Proprietary',
    description = 'The Whamcloud Lustre Monitoring and Adminisration Interface Agent',
    long_description = open('README.txt').read(),
    entry_points = {
        'console_scripts': [
            'hydra-agent = hydra_agent.cli:main',
        ],
    }
)
