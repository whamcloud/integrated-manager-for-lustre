#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import json
import os
import sys
from contextlib import contextmanager

from es.cluster.entities.cfg import EXAScalerConfig


@contextmanager
def silence_stdout():
    old_target = sys.stdout
    try:
        with open(os.devnull, "w") as new_target:
            sys.stdout = new_target
            yield new_target
    finally:
        sys.stdout = old_target


with silence_stdout():
    a = EXAScalerConfig(sys.argv[1]).to_dict()
print(json.dumps(a, indent=4, sort_keys=True))
