#!/usr/bin/env python
# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from setuptools import setup, find_packages
from chroma_diagnostics import package_version

setup(
    name='chroma-diagnostics',
    version=package_version(),
    packages=find_packages(),
    include_package_data=True,
    author="Intel Corporation",
    license='Proprietary',
    description='Collect diagnostic information on the manager or storage nodes',
    long_description=open('README.txt').read(),
    entry_points={
        'console_scripts': [
            'chroma-diagnostics = chroma_diagnostics.cli:main',
        ],
    }
)
