#!/usr/bin/env python
# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from optparse import make_option

from django.core.management.base import BaseCommand

from benchmark.metrics import Benchmark


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option("--oss", type=int, default=8, help="number of OSSes to simulate (default: 8)"),
        make_option("--ost", type=int, default=4, help="number of OSTs per OSS (default: 4)"),
        make_option("--fsname", type=str, default="stattest", help="lustre filesystem name for stats testing"),
        make_option("--server_stats", type=int, default=12, help="number of server stats"),
        make_option("--ost_stats", type=int, default=29, help="number of ost stats"),
        make_option("--mdt_stats", type=int, default=28, help="number of mdt stats"),
        make_option(
            "--duration", type=int, default=300, help="how many seconds' worth of stats to generate (default: 300)"
        ),
        make_option("--frequency", type=int, default=10, help="audit frequency for generated metrics (default: 10)"),
        make_option(
            "--no_precreate",
            action="store_true",
            default=False,
            help="don't precreate stats (could skew DB perf numbers)",
        ),
        make_option(
            "--include_create", action="store_true", default=False, help="include initial creation time in final tally"
        ),
    )
    help = "Benchmark metrics storage by simulating incoming metrics traffic"

    def handle(self, *args, **kwargs):
        bench = Benchmark(*args, **kwargs)
        bench.run()
        bench.cleanup()
