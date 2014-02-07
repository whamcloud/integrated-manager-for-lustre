#!/usr/bin/env python
#
# INTEL CONFIDENTIAL
#
# Copyright 2013 Intel Corporation All Rights Reserved.
#
# The source code contained or described herein and all documents related
# to the source code ("Material") are owned by Intel Corporation or its
# suppliers or licensors. Title to the Material remains with Intel Corporation
# or its suppliers and licensors. The Material contains trade secrets and
# proprietary and confidential information of Intel or its suppliers and
# licensors. The Material is protected by worldwide copyright and trade secret
# laws and treaty provisions. No part of the Material may be used, copied,
# reproduced, modified, published, uploaded, posted, transmitted, distributed,
# or disclosed in any way without Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellectual
# property right is granted to or conferred upon you by disclosure or delivery
# of the Materials, either expressly, by implication, inducement, estoppel or
# otherwise. Any license under such intellectual property rights must be
# express and approved by Intel in writing.


from setuptools import setup, find_packages
from chroma_agent import package_version

excludes = ["*tests*"]

setup(
    name = 'chroma-agent',
    version = package_version(),
    author = "Intel Corporation",
    author_email = "hpdd-info@intel.com",
    url = 'http://lustre.intel.com/',
    packages = find_packages(exclude=excludes),
    include_package_data = True,
    data_files=[('/usr/lib/ocf/resource.d/chroma', ['Target'])],
    license = 'Proprietary',
    description = 'The Intel Manager for Lustre Monitoring and Administration Interface Agent',
    long_description = open('README.txt').read(),
    entry_points = {
        'console_scripts': [
            'chroma-agent = chroma_agent.cli:main',
            'chroma-agent-daemon = chroma_agent.agent_daemon:main',
            'chroma-copytool-monitor = chroma_agent.copytool_monitor:main',
            'fence_chroma = chroma_agent.fence_chroma:main',
        ],
    }
)
