#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import re
import warnings
import time
from datetime import datetime as dt, timedelta as td
from dateutil.tz import tzlocal, tzutc, tzfile
import argparse
from argparse import ArgumentParser, ArgumentError
from r3d.prettytable import PrettyTable

import os
import sys
# NB: This assumes that the r3d/ app is in a subdir of the site, which
# is usually a reasonable assumption.
site_dir = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, site_dir)
from django.core.management import setup_environ
import settings
setup_environ(settings)

from django.db import transaction
from django.core.exceptions import FieldError, ObjectDoesNotExist
from django.contrib.contenttypes.models import ContentType

from r3d.models import Database


class QueryAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        delattr(namespace, 'query')

        try:
            match = re.match(r'(\w+)=([,\-\w]+)', values)
            if not match:
                raise ArgumentError(self, "bad query: %s" % values)

            ct_name = match.group(1)
            try:
                ct = ContentType.objects.get(model=ct_name)
            except ContentType.DoesNotExist:
                raise ArgumentError(self, "%s is not a valid model name" % ct_name)

            if match.group(2) == "all":
                setattr(namespace, 'db_set', ct.database_set.all())
                return

            db_set = []
            for key in match.group(2).split(","):
                for field in ['name', 'address']:
                    try:
                        kwargs = {field: key}
                        obj = ct.get_object_for_this_type(**kwargs)
                        db_set.append(ct.database_set.get(object_id=obj.pk))
                    except FieldError:
                        continue
                    except ObjectDoesNotExist:
                        raise ArgumentError(self, "%s does not identify a valid %s" % (key, ct.name))

            setattr(namespace, 'db_set', db_set)

        except TypeError:
            raise ArgumentError(self, "%s should be a string" % values)


class TimeAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        try:
            now = dt.utcnow()

            if values == "now":
                setattr(namespace, self.dest, now)
                return

            m = re.match(r'^(\-)?(\d+)(\w*)$', values)
            if m is None:
                raise ArgumentError(self, "%s should be 'now', a delta, or a timestamp" % values)

            if m.group(3) is None or m.group(3) == "":
                setattr(namespace, self.dest, dt.fromtimestamp(int(values)))
                return

            durations = ['weeks', 'days', 'hours', 'minutes', 'seconds']
            try:
                d = [d for d in durations if m.group(3) in d][0]
            except IndexError:
                raise ArgumentError(self, "%s should be one of %s" % (m.group(3), durations))

            kwargs = {d: int(m.group(2))}
            setattr(namespace, self.dest, now - td(**kwargs))
        except TypeError, e:
            import traceback
            traceback.print_exc()
            raise ArgumentError(self, "%s should be a string" % str(e))


class ArchiveAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        try:
            klass_name = values.capitalize()
            setattr(namespace, self.dest, klass_name)
            mod = __import__("r3d.models", fromlist=[klass_name])
            if not hasattr(mod, klass_name):
                raise ImportError()
        except TypeError:
            raise ArgumentError(self, "%s should be a string" % values)
        except ImportError:
            raise ArgumentError(self, "%s is not a valid archive name" % values)


# http://stackoverflow.com/a/7794220/204920
@transaction.commit_manually
def flush_transaction():
    """
    Flush the current transaction so we don't read stale data

    Use in long running processes to make sure fresh data is read from
    the database.  This is a problem with MySQL and the default
    transaction mode.  You can fix it by setting
    "transaction-isolation = READ-COMMITTED" in my.cnf or by calling
    this function at the appropriate moment.
    """
    transaction.commit()


# Stash the local timezone
_local_tz = None


def find_local_timezone():
    """
    Try to find the local timezone independently of dateutil.tz.tzlocal(),
    which doesn't work correctly within Django.  Will fall back to tzlocal()
    if all else fails, though.
    """
    def _tz_file(path):
        if os.path.exists(path):
            try:
                return tzfile(path)
            except IOError, e:
                warnings.warn("Failed to read %s: %s" % (path, e))

    global _local_tz
    if _local_tz is None:
        tz_files = ["/etc/timezone", "/etc/localtime"]
        for file in tz_files:
            _local_tz = _tz_file(file)
            if _local_tz is not None:
                return _local_tz

        # Fall back to dateutil.tz.tzlocal(), which doesn't always get
        # STD/DST correct.
        warnings.warn("Falling back to tzlocal(), which may screw up DST/STD!")
        _local_tz = tzlocal()

    return _local_tz


def pretty_time(in_time):
    local_tz = find_local_timezone()
    local_midnight = dt.now(local_tz).replace(hour=0, minute=0,
                                              second=0, microsecond=0)
    in_utc = dt.utcfromtimestamp(in_time).replace(tzinfo=tzutc())
    out_time = in_utc.astimezone(local_tz)
    if out_time < local_midnight:
        return out_time.strftime("%Y:%m:%d_%H:%M:%S")
    else:
        return out_time.strftime("%H:%M:%S")


def main():
    parser = ArgumentParser(description="R3D debug CLI")

    parser.add_argument("query", action=QueryAction,
                        help="model=(name{,name}|all), e.g. ManagedHost=all, ManagedOst=jovian-OST0000,jovian-OST0001")
    parser.add_argument("--archive", "-a", action=ArchiveAction,
                        help="Archive type to query (default: Average)",
                        default="Average")
    parser.add_argument("--datasource", "-d", action="append",
                        help="Datasource(s) to display (default: all)")
    parser.add_argument("--separate", "-s", action="store_true",
                        help="Don't aggregate per-row metrics")
    parser.add_argument("--group", "-g", action="store_true",
                        help="Display unaggregated results grouped by datasource")

    parser.add_argument("--last", "-l", action="store_true",
                        help="Fetch last reading")

    now = dt.utcnow()
    parser.add_argument("--begin", "-b", action=TimeAction,
                        default=now - td(minutes=5),
                        help="Beginning of stats request window (default: now - 5min)")
    parser.add_argument("--end", "-e", action=TimeAction,
                        default=now, help="End of stats request window (default: now)")
    parser.add_argument("--step", "-t", type=int, default=1,
                    help="Set lower limit of query resolution (default: 1 step)")

    parser.add_argument("--interval", "-n", type=int,
                        help="If supplied, refresh every N seconds")
    parser.add_argument("--debug-r3d", "-r", action="store_true",
                        help="Enable debugging output in R3D")
    ns = parser.parse_args()

    if ns.debug_r3d:
        import r3d
        r3d.DEBUG = True

    def aggregate_results(results, time, data):
        if time in results:
            for key in results[time].keys():
                a = ((results[time][key] == None) and float("NaN")) or results[time][key]
                b = ((data[key] == None) and float("NaN")) or data[key]
                results[time][key] = a + b
        else:
            results[time] = data

    def interleave_results(results, db, time, data):
        # the re.sub() is a hack but it helps to keep the display sane
        db_data = dict([[re.sub(r'(managed |stats_)', '', "%s:%s" % (db.name, key)), val] for key, val in data.items()])
        if time in results:
            results[time].update(db_data)
        else:
            results[time] = db_data

    looped = False
    while True:
        if ns.interval is not None and looped:
            # Clear the screen
            print chr(27) + "[2J"

            # Reload the set
            flush_transaction()
            ns.db_set = Database.objects.filter(id__in=[db.id for db
                                                        in ns.db_set])

            # Move the window edges
            interval = td(seconds=ns.interval)
            ns.begin += interval
            ns.end += interval

        results = {}
        for db in ns.db_set:
            if ns.last:
                row_time, data = db.fetch_last(fetch_metrics=ns.datasource)
                if ns.separate:
                    interleave_results(results, db, row_time, data)
                else:
                    aggregate_results(results, row_time, data)
            else:
                flush_transaction()
                rows = db.fetch(ns.archive, fetch_metrics=ns.datasource,
                                start_time=ns.begin, end_time=ns.end,
                                step=ns.step)
                for row in rows:
                    row_time, data = row
                    if ns.separate:
                        interleave_results(results, db, row_time, data)
                    else:
                        aggregate_results(results, row_time, data)

        if ns.separate and ns.group:
            result_keys = results.values()[0].keys()
            groups = {}
            for ds in [re.sub(r'stats_', '', ds) for ds in ns.datasource]:
                groups[ds] = sorted([key for key in result_keys if ds in key])

            columns = []
            for group in sorted(groups.keys()):
                columns.extend(groups[group])
            headers = ["time"] + columns
            table = PrettyTable(headers)
            row_times = sorted(results.keys())
            for row_time in row_times:
                row = [pretty_time(row_time)]
                for group in sorted(groups.keys()):
                    for key in groups[group]:
                        row.append(results[row_time][key])
                table.add_row(row)
        else:
            columns = sorted(results.values()[0].keys())
            headers = ["time"] + columns
            row_times = sorted(results.keys())
            table = PrettyTable(headers)
            for row_time in row_times:
                table.add_row([pretty_time(row_time)] +
                              [results[row_time][key] for key in columns])
        print table

        if ns.interval is None:
            break
        else:
            looped = True
            time.sleep(ns.interval)
