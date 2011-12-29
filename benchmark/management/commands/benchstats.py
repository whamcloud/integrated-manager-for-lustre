#!/usr/bin/env python

import time
from optparse import make_option

from django.core.management.base import BaseCommand
from django.conf import settings

from benchmark.metrics import Benchmark

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
            make_option("--oss", type=int, default=1,
                help="number of OSSes to simulate (default: 1)"),
            make_option("--ost", type=int, default=1,
                help="number of OSTs per OSS (default: 1)"),
            make_option("--fsname", type=str, default="stattest",
                help="lustre filesystem name for stats testing"),
            make_option("--server_stats", type=int, default=12,
                help="number of server stats"),
            make_option("--ost_stats", type=int, default=23,
                help="number of ost stats"),
            make_option("--mdt_stats", type=int, default=27,
                help="number of mdt stats"),
            make_option("--duration", type=int, default=300,
                help="how many seconds' worth of stats to generate (default: 300)"),
            make_option("--frequency", type=int, default=settings.AUDIT_PERIOD,
                help="audit frequency for generated metrics (default: 10)"),
            make_option("--use_flms", action='store_true', default=False,
                help="use high-speed simple stats table instead of R3D"),
            make_option("--use_flms_mem", action='store_true', default=False,
                help="use MEMORY engine type for FLMS"),
            make_option("--use_r3d_myisam", action='store_true', default=False,
                help="use MyISAM engine type for R3D tables"),
    )
    help = "Benchmark metrics storage by simulating incoming metrics traffic"

    def handle(self, *args, **kwargs):
        bench = Benchmark(*args, **kwargs)
        bench.run()
        bench.cleanup()
