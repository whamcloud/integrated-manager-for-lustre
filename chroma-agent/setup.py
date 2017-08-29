#!/usr/bin/env python
# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from setuptools import setup, find_packages
from chroma_agent import package_version

excludes = ["*tests*"]

setup(
    name = 'chroma-agent',
    version = package_version(),
    author = "Intel Corporation",
    author_email = "hpdd-info@intel.com",
    url = 'http://lustre.intel.com/',
    packages = find_packages(exclude=excludes),
    include_package_data = True,
    data_files=[('/usr/lib/ocf/resource.d/chroma', ['Target'])],
    license = 'Proprietary',
    description = 'The Intel Manager for Lustre Monitoring and Administration Interface Agent',
    long_description = open('README.txt').read(),
    entry_points = {
        'console_scripts': [
            'chroma-agent = chroma_agent.cli:main',
            'chroma-agent-daemon = chroma_agent.agent_daemon:main',
            'chroma-copytool-monitor = chroma_agent.copytool_monitor:main',
            'fence_chroma = chroma_agent.fence_chroma:main',
        ],
    }
)
