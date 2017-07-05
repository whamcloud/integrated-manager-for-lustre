#!/usr/bin/env python
# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from setuptools import setup, find_packages
from cluster_sim import package_version
from distutils.sysconfig import get_python_lib

setup(
    name = 'chroma-cluster-sim',
    version = package_version(),
    author = "Intel Corporation",
    packages = find_packages(),
    include_package_data = True,
    data_files=[(get_python_lib() + '/cluster_sim', ['cluster_sim/MDT_STAT_TEMPLATE.json', 'cluster_sim/OST_STAT_TEMPLATE.json'])],
    license = 'Proprietary',
    description = 'Cluster simulator',
    entry_points = {
        'console_scripts': [
            'cluster-sim = cluster_sim.cli:main',
            'cluster-power = cluster_sim.cli:power_main',
            'cluster-sim-benchmark = cluster_sim.benchmark:main'
        ],
    }
)
