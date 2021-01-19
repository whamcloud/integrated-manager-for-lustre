# -*- coding: utf-8 -*-
#!/usr/bin/env python

# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

from setuptools import setup, find_packages
from emf_common import package_version

# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, "README.rst"), encoding="utf-8") as f:
    long_description = f.read()

excludes = ["*tests*"]

setup(
    name="emf-common",
    version=package_version(),
    author="Whamcloud",
    author_email="emf@whamcloud.com",
    url="https://pypi.python.org/pypi/emf-common",
    packages=find_packages(exclude=excludes),
    include_package_data=True,
    license="MIT",
    description="Common library used by multiple EMF components",
    long_description=long_description,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
    ],
    keywords="EMF lustre high-availability",
)
