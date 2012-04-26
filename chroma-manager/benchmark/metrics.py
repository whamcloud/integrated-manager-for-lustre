#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import random
import sys
import time
import uuid

from django.test.simple import DjangoTestSuiteRunner
from django.db import transaction

from chroma_core.models import ManagedHost, ManagedOst, ManagedMdt, ManagedFilesystem, ManagedMgs, Volume, VolumeNode
from chroma_core.lib.lustre_audit import UpdateScan
from benchmark.generic import GenericBenchmark


class GenStatsDict(dict):
    def __getitem__(self, key):
        try:
            val = dict.__getitem__(self, key)
        except IndexError:
            val = 0

        newval = (val + random.randint(0, 1000))
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
        self.stats = {'meminfo': GenStatsDict(),
                      'cpustats': GenStatsDict(),
                      'lnet': GenStatsDict()}
        # FIXME: This should be configurable.  We don't want random
        # stat names because the metrics code will discard all but what's
        # in this list.
        for mem_stat in "SwapTotal SwapFree MemFree MemTotal".split():
            self.stats['meminfo'][mem_stat] = 0
        for lnet_stat in "recv_count send_count errors".split():
            self.stats['lnet'][lnet_stat] = 0
        for cpu_stat in "iowait idle total user system".split():
            self.stats['cpustats'][lnet_stat] = 0

    def create_entity(self, fs):
        self.entity = ManagedHost.objects.create(address=self.name)
        self.entity.metrics


class TargetGenerator(Generator):
    def __init__(self, host, fs):
        self.host = host
        super(TargetGenerator, self).__init__(fs)

    def create_volume(self):
        self.volume = Volume.objects.create()
        self.volume_node = VolumeNode.objects.create(host = self.host,
                                                     path = uuid.uuid4(),
                                                     primary = True,
                                                     use = True,
                                                     volume = self.volume)


class OstGenerator(TargetGenerator):
    def init_stats(self):
        self.stats = GenStatsDict()
        for idx in range(0, options.ost_stats):
            stat_name = "ost_stat_%d" % idx
            self.stats[stat_name] = 0

    def create_entity(self, fs):
        self.create_volume()
        self.entity = ManagedOst.create_for_volume(self.volume.pk,
                                                   name=self.name,
                                                   filesystem=fs)
        self.entity.metrics

    def __init__(self, host, oss_idx, idx, fs):
        self.name = "%s-OST%04d" % (fs.name,
                                    (oss_idx * options.ost) + idx)
        super(OstGenerator, self).__init__(host, fs)


class OssGenerator(ServerGenerator):
    def __init__(self, idx, fs):
        self.name = "oss%02d" % idx
        super(OssGenerator, self).__init__(fs)
        self.target_list = [ost for ost in
                            [OstGenerator(host=self.entity, oss_idx=idx, idx=ost_idx, fs=fs)
                                for ost_idx in range(0, options.ost)]]


class MdtGenerator(TargetGenerator):
    def init_stats(self):
        self.stats = GenStatsDict()
        for idx in range(0, options.mdt_stats):
            stat_name = "mdt_stat_%d" % idx
            self.stats[stat_name] = 0
        self.stats['num_exports'] = 1

    def create_entity(self, fs):
        self.create_volume()
        self.entity = ManagedMdt.create_for_volume(self.volume.pk,
                                                   name=self.name,
                                                   filesystem=fs)
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
        return [oss for oss in
                    [OssGenerator(idx=idx, fs=self.fs_entity)
                        for idx in range(0, options.oss)]]

    def prepare_mds_list(self):
        return [MdsGenerator(fs=self.fs_entity)]

    @transaction.commit_on_success
    def do_db_mangling(self):
        from django.db import connection

        def drop_constraints(cursor, table):
            cursor.execute("SHOW CREATE TABLE %s" % table)
            l = cursor.fetchone()[1].split()
            constraints = [l[i + 1] for i in range(0, len(l) - 1) if l[i] == 'CONSTRAINT' and l[i + 2] == 'FOREIGN']
            for constraint in constraints:
                cursor.execute("ALTER TABLE %s DROP FOREIGN KEY %s" %
                               (table, constraint.replace('`', '')))

        if options.use_r3d_myisam:
            cursor = connection.cursor()
            for table in "archive cdp cdpprep database datasource pdpprep".split():
                drop_constraints(cursor, "r3d_%s" % table)

            for table in "archive cdp cdpprep database datasource pdpprep".split():
                cursor.execute("ALTER TABLE r3d_%s ENGINE = MYISAM" % table)

    def precreate_stats(self):
        self.stats_list = []
        for i in range(0, options.duration, options.frequency):
            update_servers = []
            for server in self.server_list():
                stats = {'node': {},
                        'lustre': {'target': {}}}
                for node_stat in server.stats.keys():
                    stats['node'][node_stat] = server.stats[node_stat]

                # make this match up with what comes in from an update scan
                stats['lustre']['lnet'] = stats['node']['lnet']

                for target in server.target_list:
                    stats['lustre']['target'][target.name] = {}
                    for target_stat in target.stats.keys():
                        stats['lustre']['target'][target.name][target_stat] = target.stats[target_stat]
                update_servers.append([server.entity, stats])

            self.stats_list.append(update_servers)

    def prepare(self):
        from south.management.commands import patch_for_test_db_setup

        self.test_runner.setup_test_environment()
        # This is necessary to ensure that we use django.core.syncdb()
        # instead of south's hacked syncdb()
        patch_for_test_db_setup()
        self.old_db_config = self.test_runner.setup_databases()

        self.do_db_mangling()

        mgs_host = ManagedHost.objects.create(address="mgs")
        mgs_vol = Volume.objects.create(label="mgs")
        VolumeNode.objects.create(host = mgs_host,
                                  path = uuid.uuid4(),
                                  primary = True,
                                  use = True,
                                  volume = mgs_vol)
        self.mgs = ManagedMgs.create_for_volume(mgs_vol.pk, name="MGS")
        self.fs_entity = ManagedFilesystem.objects.create(name=options.fsname,
                                                          mgs=self.mgs)
        self.oss_list = self.prepare_oss_list()
        self.mds_list = self.prepare_mds_list()

        sys.stderr.write("Precreating stats... ")
        self.precreate_stats()
        sys.stderr.write(" Done.\n")

    def server_list(self):
        return self.mds_list + self.oss_list

    @transaction.commit_on_success
    def store_metrics(self, scan):
        return scan.store_metrics()

    def run(self):
        def t2s(t):
            return time.strftime("%H:%M:%S", time.localtime(t))

        scan = UpdateScan()
        run_start = time.time()
        run_count = 0
        create_interval = 0
        create_count = 0
        print "start: %s, stop: %s" % (t2s(run_start),
                                       t2s(run_start + options.duration))
        for update_time in range(int(run_start),
                                 int(run_start + options.duration),
                                 options.frequency):
            sys.stderr.write(t2s(update_time))
            store_start = time.time()
            count = 0

            stats_idx = ((update_time - int(run_start)) / options.frequency)
            for server_stats in self.stats_list[stats_idx]:
                scan.host = server_stats[0]
                scan.host_data = {'metrics': {'raw': server_stats[1]}}
                scan.update_time = update_time
                count += self.store_metrics(scan)

            run_count += count
            store_end = time.time()
            interval = store_end - store_start
            rate = count / interval
            meter = "+" if interval < options.frequency else "-"
            sys.stderr.write(": inserted %d stats (rate: %lf stats/sec) %s\r" % (count, rate, meter))

            if not options.include_create and update_time == int(run_start):
                create_interval = interval
                create_count = count

        run_end = time.time()

        run_info = LazyStruct()
        run_info.run_count = run_count
        run_info.run_interval = run_end - run_start - create_interval
        run_info.run_rate = (run_count - create_count) / run_info.run_interval
        run_info.create_interval = create_interval
        run_info.create_count = create_count

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
                if 'processor' in line:
                    count += 1
                    continue

                if 'cpu MHz' in line:
                    speed = float(line.split()[3])
                    continue

            return {'count': count, 'speed': speed}

        def _mem_info():
            mem_info = {}
            for line in _read_lines("/proc/meminfo"):
                for query in ["MemTotal", "MemFree", "SwapTotal", "SwapFree"]:
                    if query in line:
                        mem_info[query] = float(line.split()[1])
                        break

            mem_info['pct_mem_used'] = ((mem_info['MemTotal'] - mem_info['MemFree']) / mem_info['MemTotal']) * 100
            mem_info['pct_swap_used'] = ((mem_info['SwapTotal'] - mem_info['SwapFree']) / mem_info['SwapTotal']) * 100
            return mem_info

        profile = LazyStruct()
        cpu_info = _cpu_info()
        profile.cpu_count = cpu_info['count']
        profile.cpu_speed = cpu_info['speed']
        mem_info = _mem_info()
        profile.mem_total = mem_info['MemTotal']
        profile.mem_pct_used = mem_info['pct_mem_used']
        profile.swap_total = mem_info['SwapTotal']
        profile.swap_pct_used = mem_info['pct_swap_used']

        return profile

    # TODO: Customizable output formats (csv, tsv, etc.)
    def print_report(self, run_info):
        profile = self.profile_system()
        print "CPUs: %d @ %.2f GHz, Mem: %d MB real (%.2f%% used) / %d MB swap (%.2f%% used)" % (profile.cpu_count, (profile.cpu_speed / 1000), (profile.mem_total / 1000), profile.mem_pct_used, (profile.swap_total / 1000), profile.swap_pct_used)
        print "counts: OSS: %d, OSTs/OSS: %d (%d total); stats: OST: %d, MDT: %d, server: %d" % (options.oss, options.ost, (options.oss * options.ost), options.ost_stats, options.mdt_stats, options.server_stats)
        print "run count (%d stats) / run time (%.2f sec) = run rate (%.2f stats/sec)" % (run_info.run_count, run_info.run_interval, run_info.run_rate)

    def cleanup(self):
        self.test_runner.teardown_databases(self.old_db_config)
        self.test_runner.teardown_test_environment()
