#!/usr/bin/env python

import time
import re
import math, random
import os, sys
import argparse

# Generate a series of data points for use in testing R3D's fidelity
# to rrdtool's design.
# ./gen_test_series.py --start=920804400 --step=5 --rows=10 DS:Counter:60:0:U:1234 DS:Gauge:U:U
# 920804400:1234:456
# ...
# 920804450:1832:23

def ds_str(string):
    ds_re = re.compile(r"""
    ^DS:
    (?P<type>(Counter|Gauge|Derive|Absolute)):
    (?P<heartbeat>\d+):
    (?P<min>[\d\.U]+):
    (?P<max>[\d\.U]+)
    (:(?P<start>\d+))?
    $
    """, re.VERBOSE|re.IGNORECASE)

    match = ds_re.match(string)
    if match:
        return match
    else:
        raise ValueError

def setup_parser():
    parser = argparse.ArgumentParser(
        description="Generate test data suitable for rrdtool or R3D update."
    )
    parser.add_argument(
        "--start", type=int, default=int(time.time() - 86400),
        help="start time for the series (default: now - 86400)",
    )
    parser.add_argument(
        "--step", type=int, default=300,
        help="interval between data points (default: 300)"
    )
    parser.add_argument(
        "--rows", type=int, default=288,
        help="number of rows to generate (default 288)"
    )
    parser.add_argument(
        "--randunk", action="store_true", default=False,
        help="randomly inject unknown (U) datapoints into output stream"
    )
    parser.add_argument(
        "--randslow", action="store_true", default=False,
        help="randomly generate series data slower than the expected input interval "
    )
    parser.add_argument(
        "--randfast", action="store_true", default=False,
        help="randomly generate series data faster than the expected input interval"
    )
    parser.add_argument(
        "ds_list", type=ds_str, help="list of rrdtool-style DS definitions",
        nargs="+", metavar="DS:TYPE:heartbeat:min:max[:start]"
    )
    return parser

class Datasource(object):
    def __init__(self, db_start=int(time.time()), db_step=1, rows=1,
                 heartbeat=1, min_val="U", max_val="U", ds_start=0):
        self.db_start = db_start
        self.db_step = db_step
        self.rows = rows
        self.heartbeat = heartbeat
        self.min_val = float(min_val) if min_val != "U" else 0.0
        self.max_val = float(max_val) if max_val != "U" else 999999999999.0
        self.counter = ds_start if ds_start else 0

    def _next_value(self, row_time):
        self.counter += 1

    def value(self, row_time):
        self._next_value(row_time)
        fn = lambda v: "U" if math.isnan(v) else v
        return fn(self.counter)

class Counter(Datasource):
    """Generates steadily-incrementing values."""
    def _next_value(self, row_time):
        self.counter += row_time % (self.db_step * random.randint(1, 1000))

class Absolute(Datasource):
    """Generates rapidly-incrementing, often-wrapping values."""
    def _next_value(self, row_time):
        # ensure that we're never multiplying by zero
        self.counter += 1.0
        self.counter *= random.uniform(self.min_val, self.max_val)
        if self.counter > self.max_val:
            self.counter = self.min_val
            self._next_value(row_time)

class Gauge(Datasource):
    """Generates completely random (between min/max) values."""
    def _next_value(self, row_time):
        self.counter = random.uniform(self.min_val, self.max_val)

class Derive(Datasource):
    """Generates steadily-incrementing values."""
    def _next_value(self, row_time):
        self.counter += row_time % (self.db_step * random.randint(1, 1000))

def generate_row(row_time):
    row = ["%d" % row_time]
    for ds in ds_objs:
        if args.randunk and (row_time % random.random()) > 0.7:
            row.append("U")
        else:
            row.append("%lf" % ds.value(row_time))

    print ":".join(row)    

if __name__ == "__main__":
    args = setup_parser().parse_args()

    ds_objs = []
    for ds_match in args.ds_list:
        ds_klass = globals()[ds_match.group('type').lower().capitalize()]
        ds_objs.append(
            ds_klass(
                db_start=args.start,
                db_step=args.step,
                rows=args.rows,
                heartbeat=ds_match.group('heartbeat'),
                min_val=ds_match.group('min'),
                max_val=ds_match.group('max'),
                ds_start=ds_match.group('start')
            )
        )

    skip_until = 0
    for row_time in range(args.start,
                          (args.start + (args.step * args.rows)), args.step):
        if row_time < skip_until:
            continue
        elif skip_until > 0 and row_time >= skip_until:
            print "# ending slowdown"
            skip_until = 0

        if args.randfast and (row_time % random.random()) > 0.9:
            print "# starting fast series"
            for extra in range((row_time - args.step), row_time, 1):
                generate_row(extra)
            print "# ending fast series"

        if args.randslow and (row_time % random.random()) > 0.9:
            print "# starting slowdown"
            skip_until = row_time + (args.step * random.randint(1, 10))

        generate_row(row_time)

