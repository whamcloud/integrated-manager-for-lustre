#!/usr/bin/env python

# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

from setuptools import setup

__version__ = "2.4.0"

setup(
    name="emf-sos-plugin",
    version=__version__,
    author="Whamcloud",
    author_email="iml@whamcloud.com",
    url="https://pypi.python.org/pypi/iml-sos-plugin",
    packages=["sos.plugins", "sos"],
    include_package_data=True,
    license="MIT",
    description="EMF sosreport plugin",
    long_description="""
    A sosreport plugin for collecting EMF data
    """,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
    ],
    keywords="IML EMF lustre high-availability",
)
