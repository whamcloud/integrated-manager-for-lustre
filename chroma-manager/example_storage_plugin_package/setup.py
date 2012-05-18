#!/usr/bin/env python
#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from setuptools import setup, find_packages

excludes = ["*.tests", "*.tests.*", "tests.*", "tests"]

setup(
    name = 'example-storage-plugin',
    version = 1.0,
    author = "Your Name",
    author_email = "you@example.com",
    url = 'http://www.example.com',
    packages = find_packages(exclude=excludes),
    license = 'Proprietary',
    description = 'An example storage plugin',
    long_description = "This the example storage plugin by Whamcloud, Inc.",
)
