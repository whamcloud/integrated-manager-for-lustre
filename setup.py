#!/usr/bin/env python
#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from distutils.core import setup
from r3d import __version__

setup(
    name = 'django-r3d',
    version = __version__,
    author = "Whamcloud, Inc.",
    author_email = "info@whamcloud.com",
    packages = ['r3d', 'r3d/migrations', 'r3d/tests', 'r3d/tests/unit', 'r3d/tests/integration'],
    package_data = {'r3d/tests': ['data/*']},
    url = 'http://www.whamcloud.com/',
    license = 'GPL',
    description = 'Relational Round-Robin Databases (R3D) for Django', 
    long_description = open('README.txt').read(),
)
