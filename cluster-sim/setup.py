#!/usr/bin/env python
#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from setuptools import setup, find_packages
from cluster_sim import package_version

setup(
    name = 'chroma-cluster-sim',
    version = package_version(),
    author = "Intel Corporation",
    packages = find_packages(),
    include_package_data = True,
    data_files=[('/usr/lib/python2.6/site-packages/cluster_sim', ['cluster_sim/MDT_STAT_TEMPLATE.json', 'cluster_sim/OST_STAT_TEMPLATE.json'])],
    license = 'Proprietary',
    description = 'Cluster simulator',
    entry_points = {
        'console_scripts': [
            'cluster-sim = cluster_sim.cli:main',
            'cluster-sim-benchmark = cluster_sim.benchmark:main'
        ],
    }
)
