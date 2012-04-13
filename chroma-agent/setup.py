#!/usr/bin/env python
#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from setuptools import setup, find_packages
from chroma_agent import __version__

excludes = ["*.tests", "*.tests.*", "tests.*", "tests"]

setup(
    name = 'chroma-agent',
    version = __version__,
    author = "Whamcloud, Inc.",
    author_email = "info@whamcloud.com",
    url = 'http://www.whamcloud.com/',
    packages = find_packages(exclude=excludes),
    data_files=[('/usr/lib/ocf/resource.d/chroma', ['Target'])],
    license = 'Proprietary',
    description = 'The Whamcloud Lustre Monitoring and Adminisration Interface Agent',
    long_description = open('README.txt').read(),
    entry_points = {
        'console_scripts': [
            'chroma-agent = chroma_agent.cli:main',
        ],
    }
)
