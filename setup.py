# -*- coding: utf-8 -*-
#!/usr/bin/env python
# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from setuptools import setup, find_packages, findall
from chroma_manager import package_version
from re import sub

excludes = [
]

setup(
    name = 'iml-manager',
    version = package_version(),
    author = "Intel Corporation",
    author_email = "iml@whamcloud.com",
    url = 'https://pypi.python.org/pypi/iml-manager',
    license='MIT',
    description = 'The Integrated Manager for Lustre software Monitoring and Administration Interface',
    long_description = open('README.txt').read(),
    packages = find_packages(exclude=excludes) + [''],
    # include_package_data would be far more convenient, but the top-level
    # package confuses setuptools. As a ridiculous hackaround, we'll game
    # things by prepending a dot to top-level datafiles (which implies
    # file creation/cleanup in the Makefile) to deal with the fact
    # that setuptools wants to strip the first character off the filename.
    package_data={
        '': [
            ".chroma-manager.py", ".storage_server.repo",
            ".chroma-manager.conf.template", ".mime.types"
        ],
        'chroma_core': ["fixtures/default_power_types.json"],
        'polymorphic': ["COPYING"],
        'tests': [
            "integration/run_tests", "integration/*/*.json", "sample_data/*",
            "integration/core/clear_ha_el?.sh"
        ]
    },
    scripts=["chroma-host-discover"],
    entry_points={
        'console_scripts': [
            'chroma-config = chroma_core.lib.service_config:chroma_config',
            'chroma = chroma_cli.main:standard_cli'
        ]
    })
