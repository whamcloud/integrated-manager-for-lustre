# -*- coding: utf-8 -*-
# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import sys
import os

project_dir = None
pwd_parts = os.environ['PWD'].split(os.sep)
while not project_dir:
    settings_path = "/" + os.path.join(*(pwd_parts + ["settings.py"]))
    if os.path.exists(settings_path):
        project_dir = "/" + os.path.join(*pwd_parts)
    else:
        pwd_parts = pwd_parts[0:-1]
        if len(pwd_parts) == 0:
            raise RuntimeError("Can't find settings.py")

sys.path.append(project_dir)

agent_dir = os.path.join(*(list(os.path.split(project_dir)[0:-1]) + ['chroma-agent']))
sys.path.append(agent_dir)

simulator_dir = os.path.join(*(list(os.path.split(project_dir)[0:-1]) + ['cluster-sim']))
sys.path.append(simulator_dir)

from docs.conf_common import *

project = u'Intel® Manager for Lustre* software Internals'
master_doc = 'index'

graphviz_dot_args = [
        "-Gfontname=Arial bold", "-Gfontsize=10", "-Gshape=box", "-Gpenwidth=0.5", "-Gfontweight=bold",
        "-Nfontname=Arial", "-Nfontsize=10", "-Nshape=box", "-Nstyle=rounded", "-Npenwidth=1.2", "-Ncolor=lightblue",
        "-Efontname=Arial", "-Efontsize=8", "-Epenwidth=0.5"
]

extensions.append('sphinx.ext.viewcode')
extensions.append('sphinx.ext.graphviz')
