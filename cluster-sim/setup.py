#!/usr/bin/env python
#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from setuptools import setup, find_packages

setup(
    name = 'cluster-sim',
    version = '0.0.1',
    author = "Intel Corporation",
    packages = find_packages(),
    include_package_data = True,
    data_files=[],
    license = 'Proprietary',
    description = 'Cluster simulator',
    entry_points = {
        'console_scripts': [
            'cluster-sim = cluster_sim.cli:main',
            'cluster-power = cluster_sim.cli:power_main'
        ],
    }
)
