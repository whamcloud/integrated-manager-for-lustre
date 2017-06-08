#!/usr/bin/env python
# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from setuptools import setup, find_packages
from chroma_common import package_version

setup(
    name = 'chroma-common',
    version = package_version(),
    packages = find_packages(),
    include_package_data = True,
    author = "Intel(R) Corporation",
    description = 'Common library used by both agent and manager',
    long_description = open('README.txt').read()
)
