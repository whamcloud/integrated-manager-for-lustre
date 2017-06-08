#!/usr/bin/env python
# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from setuptools import setup, find_packages
from chroma_common import package_version

excludes = ["*tests*"]

setup(
    name = 'chroma-common',
    version = package_version(),
    packages = find_packages(exclude=excludes),
    include_package_data = True,
    author = "Intel(R) Corporation",
    author_email = "hpdd-info@intel.com",
    url = 'http://lustre.intel.com/',
    description = 'Common library used by both agent and manager',
    long_description = open('README.txt').read()
)
