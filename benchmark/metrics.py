# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import random
import os
import sys
import time
import uuid

from django.test.simple import DjangoTestSuiteRunner

from chroma_core.models import (
    ManagedHost,
    ManagedOst,
    ManagedMdt,
    ManagedFilesystem,
    ManagedMgs,
    Volume,
    VolumeNode,
    Stats,
)
from chroma_core.services.lustre_audit.update_scan import UpdateScan
from benchmark.generic import GenericBenchmark


class GenStatsDict(dict):
    def __getitem__(self, key):
        try:
            val = dict.__getitem__(self, key)
        except IndexError:
            val = 0

        newval = val + random.randint(0, 1000)
        self[key] = newval

        return newval


class Generator(object):
    def __init__(self, fs):
        self.create_entity(fs)
        self.init_stats()

    def __repr__(self):
        return "%s %s" % (self.name, self.stats)


class ServerGenerator(Generator):
    def __repr__(self):
        return "%s %s %s" % (self.name, self.stats, self.target_list)

    def init_stats(self):
        self.stats = {"meminfo": GenStatsDict(), "cpustats": GenStatsDict(), "lnet": GenStatsDict()}
        # This is an artifact of when server stats were configurable.
        # Setting --server_stats to anything other than 0 has no effect
        # on the number of stats generated.  Leaving it there so we
        # can still specify 0 server stats to turn them off completely.
        if options.server_stats == 0:
            return

        # FIXME: This should be configurable.  We don't want random
        # stat names because the metrics code will discard all but what's
        # in this list.
        for mem_stat in "SwapTotal SwapFree MemFree MemTotal".split():
            self.stats["meminfo"][mem_stat] = 0
        for lnet_stat in "recv_count send_count errors".split():
            self.stats["lnet"][lnet_stat] = 0
        for cpu_stat in "iowait idle total user system".split():
            self.stats["cpustats"][cpu_stat] = 0

    def create_entity(self, fs):
        self.entity = ManagedHost.objects.create(address=self.name, fqdn=self.name, nodename=self.name)
        self.entity.metrics


class TargetGenerator(Generator):
    def __init__(self, host, fs):
        self.host = host
        super(TargetGenerator, self).__init__(fs)

    def create_volume(self):
        self.volume = Volume.objects.create()
        self.volume_node = VolumeNode.objects.create(
            host=self.host, path=uuid.uuid4(), primary=True, use=True, volume=self.volume
        )


class OstGenerator(TargetGenerator):
    def init_stats(self):
        self.stats = GenStatsDict()
        for idx in range(0, options.ost_stats):
            stat_name = "ost_stat_%d" % idx
            self.stats[stat_name] = 0

    def create_entity(self, fs):
        self.create_volume()
        self.entity, mounts = ManagedOst.create_for_volume(self.volume.pk, name=self.name, filesystem=fs)
        self.entity.metrics

    def __init__(self, host, oss_idx, idx, fs):
        self.name = "%s-OST%04d" % (fs.name, (oss_idx * options.ost) + idx)
        super(OstGenerator, self).__init__(host, fs)


class OssGenerator(ServerGenerator):
    def __init__(self, idx, fs):
        self.name = "oss%02d" % idx
        super(OssGenerator, self).__init__(fs)
        self.target_list = [
            ost
            for ost in [
                OstGenerator(host=self.entity, oss_idx=idx, idx=ost_idx, fs=fs) for ost_idx in range(0, options.ost)
            ]
        ]


class MdtGenerator(TargetGenerator):
    def init_stats(self):
        self.stats = GenStatsDict()
        for idx in range(0, options.mdt_stats):
            stat_name = "mdt_stat_%d" % idx
            self.stats[stat_name] = 0
        if options.mdt_stats > 0:
            self.stats["client_count"] = 1

    def create_entity(self, fs):
        self.create_volume()
        self.entity, mounts = ManagedMdt.create_for_volume(self.volume.pk, name=self.name, filesystem=fs)
        self.entity.metrics

    def __init__(self, host, fs):
        self.name = "%s-MDT%04d" % (fs.name, 0)
        super(MdtGenerator, self).__init__(host, fs)


class MdsGenerator(ServerGenerator):
    def __init__(self, fs):
        self.name = "mds00"
        super(MdsGenerator, self).__init__(fs)
        self.target_list = [MdtGenerator(host=self.entity, fs=fs)]


class LazyStruct(object):
    """
    It's kind of like a struct, and I'm lazy.
    """

    def __init__(self, **kwargs):
        self.__dict__ = kwargs

    def __getattr__(self, key):
        return self.__dict__[key]


# global option store
options = None


class Benchmark(GenericBenchmark):
    def __init__(self, *args, **kwargs):
        global options
        options = LazyStruct(**kwargs)
        self.test_runner = DjangoTestSuiteRunner()
        self.prepare()

    def prepare_oss_list(self):
        return [oss for oss in [OssGenerator(idx=idx, fs=self.fs_entity) for idx in range(0, options.oss)]]

    def prepare_mds_list(self):
        return [MdsGenerator(fs=self.fs_entity)]

    def step_stats(self):
        """Generate stats for all servers in a single step"""
        update_servers = []
        for server in self.server_list():
            stats = {"node": {}, "lustre": {"target": {}}}
            for node_stat in server.stats.keys():
                stats["node"][node_stat] = server.stats[node_stat]

            # make this match up with what comes in from an update scan
            stats["lustre"]["lnet"] = stats["node"]["lnet"]

            for target in server.target_list:
                stats["lustre"]["target"][target.name] = {}
                for target_stat in target.stats.keys():
                    stats["lustre"]["target"][target.name][target_stat] = target.stats[target_stat]
            update_servers.append([server.entity, stats])

        return update_servers

    def precreate_stats(self):
        self.stats_list = []

        steps = range(0, options.duration, options.frequency)
        for idx, v in enumerate(steps):
            sys.stderr.write("\rPrecreating stats... (%d/%d)" % (idx, len(steps)))
            self.stats_list.append(self.step_stats())

        sys.stderr.write("\rPrecreating stats... Done.        \n")

    def prepare(self):
        from south.management.commands import patch_for_test_db_setup

        self.test_runner.setup_test_environment()
        # This is necessary to ensure that we use django.core.syncdb()
        # instead of south's hacked syncdb()
        patch_for_test_db_setup()
        self.old_db_config = self.test_runner.setup_databases()

        mgs_host = ManagedHost.objects.create(address="mgs", fqdn="mgs", nodename="mgs")
        mgs_vol = Volume.objects.create(label="mgs")
        VolumeNode.objects.create(host=mgs_host, path=uuid.uuid4(), primary=True, use=True, volume=mgs_vol)
        self.mgs, mounts = ManagedMgs.create_for_volume(mgs_vol.pk, name="MGS")
        self.fs_entity = ManagedFilesystem.objects.create(name=options.fsname, mgs=self.mgs)
        self.oss_list = self.prepare_oss_list()
        self.mds_list = self.prepare_mds_list()

        if not options.no_precreate:
            self.precreate_stats()

    def get_stats_size(self):
        stats_size = LazyStruct()
        from django.db import connection

        cursor = connection.cursor()
        if "postgres" in connection.settings_dict["ENGINE"]:
            stats_size.row_count = stats_size.data = stats_size.index = 0

            for model in Stats:
                cursor.execute(
                    "select count(id) as rows, pg_relation_size('{0}') as data_length, pg_total_relation_size('{0}') - pg_relation_size('{0}') as index_length from {0}".format(
                        model._meta.db_table
                    )
                )
                rows, data, index = cursor.fetchone()
                stats_size.row_count += rows
                stats_size.data += data
                stats_size.index += index
        else:
            raise RuntimeError("Unsupported DB: %s" % connection.settings_dict["ENGINE"])
        return stats_size

    def server_list(self):
        return self.mds_list + self.oss_list

    def store_metrics(self, scan):
        return scan.store_metrics()

    def run(self):
        def t2s(t):
            return time.strftime("%H:%M:%S", time.localtime(t))

        def s2s(s):
            if s > 600:
                from datetime import timedelta, datetime

                d = timedelta(seconds=int(s)) + datetime(1, 1, 1)
                return "%.2d:%.2d:%.2d:%.2d" % (d.day - 1, d.hour, d.minute, d.second)
            else:
                return "%d" % s

        stats_size_start = self.get_stats_size()

        scan = UpdateScan()
        run_start = time.time()
        run_count = 0
        create_interval = 0
        create_count = 0
        start_la = os.getloadavg()
        last_width = 0
        print("window start: %s, window stop: %s" % (t2s(run_start), t2s(run_start + options.duration)))
        update_times = range(int(run_start), int(run_start + options.duration), options.frequency)
        for stats_idx, update_time in enumerate(update_times):
            new_timing_line = "\r%s" % t2s(update_time)
            sys.stderr.write(new_timing_line)
            store_start = time.time()
            count = 0

            if options.no_precreate:
                step_stats_list = self.step_stats()
            else:
                step_stats_list = self.stats_list[stats_idx]

            server_stats_count = 0
            for step_stats in step_stats_list:
                scan.host = step_stats[0]
                scan.host_data = {"metrics": {"raw": step_stats[1]}}
                scan.update_time = update_time
                count += self.store_metrics(scan)
                # Since we've hard-coded the server stats, we need to record
                # the actual number to make the reporting accurate.
                if options.server_stats == 0:
                    for key in ["meminfo", "lnet", "cpustats"]:
                        server_stats_count += len(step_stats[1]["node"][key])

            # Terrible hack to make reporting accurate.
            if options.server_stats == 0:
                options.server_stats = server_stats_count

            run_count += count
            store_end = time.time()
            interval = store_end - store_start
            rate = count / interval
            meter = "+" if interval < options.frequency else "-"
            seconds_left = (len(update_times) - stats_idx) * interval
            timing_stats = ": inserted %d stats (rate: %lf stats/sec, complete in: %s) %s" % (
                count,
                rate,
                s2s(seconds_left),
                meter,
            )
            current_line_width = len(new_timing_line + timing_stats)
            if current_line_width < last_width:
                sys.stderr.write(new_timing_line + timing_stats + " " * (last_width - current_line_width))
            else:
                sys.stderr.write(timing_stats)
            last_width = current_line_width

            if not options.include_create and update_time == int(run_start):
                create_interval = interval
                create_count = count

        run_end = time.time()
        end_la = os.getloadavg()

        stats_size_end = self.get_stats_size()

        run_info = LazyStruct()
        run_info.step_count = options.duration / options.frequency
        run_info.run_count = run_count
        run_info.run_interval = run_end - run_start - create_interval
        run_info.run_rate = (run_count - create_count) / run_info.run_interval
        run_info.create_interval = create_interval
        run_info.create_count = create_count
        run_info.start_load_avg = start_la
        run_info.end_load_avg = end_la
        run_info.stats_data_used = stats_size_end.data - stats_size_start.data
        run_info.stats_index_used = stats_size_end.index - stats_size_start.index
        run_info.stats_rows_used = stats_size_end.row_count - stats_size_start.row_count

        self.print_report(run_info)

    def profile_system(self):
        def _read_lines(filename):
            fh = open(filename)
            try:
                return [line.rstrip("\n") for line in fh.readlines()]
            finally:
                fh.close()

        def _cpu_info():
            count = 0
            speed = 0
            for line in _read_lines("/proc/cpuinfo"):
                if "processor" in line:
                    count += 1
                    continue

                if "cpu MHz" in line:
                    speed = float(line.split()[3])
                    continue

            return {"count": count, "speed": speed}

        def _mem_info():
            mem_info = {}
            for line in _read_lines("/proc/meminfo"):
                for query in ["MemTotal", "MemFree", "SwapTotal", "SwapFree"]:
                    if query in line:
                        mem_info[query] = float(line.split()[1])
                        break

            mem_info["pct_mem_used"] = ((mem_info["MemTotal"] - mem_info["MemFree"]) / mem_info["MemTotal"]) * 100
            try:
                mem_info["pct_swap_used"] = (
                    (mem_info["SwapTotal"] - mem_info["SwapFree"]) / mem_info["SwapTotal"]
                ) * 100
            except ZeroDivisionError:
                mem_info["pct_swap_used"] = 0.0
            return mem_info

        profile = LazyStruct()
        cpu_info = _cpu_info()
        profile.cpu_count = cpu_info["count"]
        profile.cpu_speed = cpu_info["speed"]
        mem_info = _mem_info()
        profile.mem_total = mem_info["MemTotal"]
        profile.mem_pct_used = mem_info["pct_mem_used"]
        profile.swap_total = mem_info["SwapTotal"]
        profile.swap_pct_used = mem_info["pct_swap_used"]

        return profile

    # TODO: Customizable output formats (csv, tsv, etc.)
    def print_report(self, run_info):
        print("\n")
        try:
            profile = self.profile_system()
            print(
                "CPUs: %d @ %.2f GHz, Mem: %d MB real (%.2f%% used) / %d MB swap (%.2f%% used)"
                % (
                    profile.cpu_count,
                    (profile.cpu_speed / 1000),
                    (profile.mem_total / 1000),
                    profile.mem_pct_used,
                    (profile.swap_total / 1000),
                    profile.swap_pct_used,
                )
            )
        except IOError:
            print("No system profile available (on a mac?)")
        print(
            "Load averages (1/5/15): start: %.2f/%.2f/%.2f, end: %.2f/%.2f/%.2f"
            % (run_info.start_load_avg + run_info.end_load_avg)
        )
        print(
            "counts: OSS: %d, OSTs/OSS: %d (%d total); stats-per: OSS: %d, MDS: %d"
            % (
                options.oss,
                options.ost,
                (options.oss * options.ost),
                ((options.ost * options.ost_stats) + options.server_stats),
                (options.mdt_stats + options.server_stats),
            )
        )
        print(
            "run count (%d stats) / run time (%.2f sec) = run rate (%.2f stats/sec)"
            % (run_info.run_count, run_info.run_interval, run_info.run_rate)
        )
        print(
            "%d steps, %d stats/step, duration %d"
            % (run_info.step_count, run_info.run_count / run_info.step_count, options.duration)
        )

        def _to_mb(in_bytes):
            return in_bytes * 1.0 / (1024 * 1024)

        stats_total_used = run_info.stats_data_used + run_info.stats_index_used
        print(
            "stats rows: %d, space used: %.2f MB (%.2f MB data, %.2f MB index)"
            % (
                run_info.stats_rows_used,
                _to_mb(stats_total_used),
                _to_mb(run_info.stats_data_used),
                _to_mb(run_info.stats_index_used),
            )
        )

    def cleanup(self):
        self.test_runner.teardown_databases(self.old_db_config)
        self.test_runner.teardown_test_environment()
