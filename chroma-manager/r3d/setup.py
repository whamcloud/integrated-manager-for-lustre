#!/usr/bin/env python
#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from setuptools import setup, find_packages
from r3d import __version__

setup(
    name = 'django-r3d',
    version = __version__,
    author = "Whamcloud, Inc.",
    author_email = "info@whamcloud.com",
    packages = find_packages(),
    package_data = {'r3d.tests': ['sample_data/*']},
    url = 'http://www.whamcloud.com/',
    license = 'GPL',
    description = 'Relational Round-Robin Databases (R3D) for Django',
    long_description = open('README.txt').read(),
)
