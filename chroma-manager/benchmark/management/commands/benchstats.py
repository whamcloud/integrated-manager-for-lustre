#!/usr/bin/env python
#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2015 Intel Corporation All Rights Reserved.
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


from optparse import make_option

from django.core.management.base import BaseCommand

from benchmark.metrics import Benchmark


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
            make_option("--oss", type=int, default=8,
                help="number of OSSes to simulate (default: 8)"),
            make_option("--ost", type=int, default=4,
                help="number of OSTs per OSS (default: 4)"),
            make_option("--fsname", type=str, default="stattest",
                help="lustre filesystem name for stats testing"),
            make_option("--server_stats", type=int, default=12,
                help="number of server stats"),
            make_option("--ost_stats", type=int, default=29,
                help="number of ost stats"),
            make_option("--mdt_stats", type=int, default=28,
                help="number of mdt stats"),
            make_option("--duration", type=int, default=300,
                help="how many seconds' worth of stats to generate (default: 300)"),
            make_option("--frequency", type=int, default=10,
                help="audit frequency for generated metrics (default: 10)"),
            make_option("--no_precreate", action='store_true', default=False,
                help="don't precreate stats (could skew DB perf numbers)"),
            make_option("--include_create", action='store_true', default=False,
                help="include initial creation time in final tally"),
    )
    help = "Benchmark metrics storage by simulating incoming metrics traffic"

    def handle(self, *args, **kwargs):
        bench = Benchmark(*args, **kwargs)
        bench.run()
        bench.cleanup()
