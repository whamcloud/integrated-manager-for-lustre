#!/usr/bin/env python
#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from setuptools import setup, find_packages
from chroma_agent.production_version import PACKAGE_VERSION

excludes = ["*tests*"]

setup(
    name = 'chroma-agent',
    version = PACKAGE_VERSION,
    author = "Whamcloud, Inc.",
    author_email = "info@whamcloud.com",
    url = 'http://www.whamcloud.com/',
    packages = find_packages(exclude=excludes),
    include_package_data = True,
    data_files=[('/usr/lib/ocf/resource.d/chroma', ['Target'])],
    license = 'Proprietary',
    description = 'The Whamcloud Lustre Monitoring and Adminisration Interface Agent',
    long_description = open('README.txt').read(),
    entry_points = {
        'console_scripts': [
            'chroma-agent = chroma_agent.cli:main',
            'chroma-agent-daemon = chroma_agent.agent_daemon:main',
            'fence_chroma = chroma_agent.fence_chroma:main',
        ],
    }
)
