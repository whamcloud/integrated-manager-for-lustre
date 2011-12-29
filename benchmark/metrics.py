import random
import sys, time

from django.contrib.contenttypes.models import ContentType
from django.test.simple import DjangoTestSuiteRunner
from django.db import transaction

import settings

from configure.models import ManagedHost, ManagedOst, ManagedMdt, ManagedFilesystem, ManagedMgs, ManagedTargetMount, Lun, LunNode
from monitor.lib.lustre_audit import UpdateScan
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
    def __init__(self, fs, **kwargs):
        self.create_entity(fs)
        self.init_stats(**kwargs)

    def __repr__(self):
        return "%s %s" % (self.name, self.stats)

class ServerGenerator(Generator):
    def __repr__(self):
        return "%s %s %s" % (self.name, self.stats, self.target_list)

    def init_stats(self, **kwargs):
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
        self.entity = ManagedHost.objects.get_or_create(address=self.name)[0]
        self.entity.metrics

class TargetGenerator(Generator):
    def __init__(self, host, fs, **kwargs):
        self.host = host
        super(TargetGenerator, self).__init__(fs, **kwargs)

    def create_entity(self, fs):
        import uuid
        # Need to gin this stuff up to make the metrics layer happy.  Sigh.
        lun = Lun.objects.create(shareable = 0)
        lun_node = LunNode.objects.create(host = self.host,
                                          path = uuid.uuid4(),
                                          lun = lun)
        ManagedTargetMount.objects.create(block_device=lun_node,
                                          target = self.entity,
                                          host = self.host,
                                          mount_point = uuid.uuid4(),
                                          primary = True)

class OstGenerator(TargetGenerator):
    def init_stats(self, **kwargs):
        self.stats = GenStatsDict()
        for idx in range(0, kwargs['ost_stats']):
            stat_name = "ost_stat_%d" % idx
            self.stats[stat_name] = 0

    def create_entity(self, fs):
        self.entity = ManagedOst.objects.get_or_create(name=self.name,
                                                       filesystem=fs)[0]
        self.entity.metrics
        super(OstGenerator, self).create_entity(fs)

    def __init__(self, host, oss_idx, idx, fs, **kwargs):
        self.name = "%s-OST%04d" % (kwargs['fsname'],
                                    (oss_idx * kwargs['ost']) + idx)
        super(OstGenerator, self).__init__(host, fs, **kwargs)

class OssGenerator(ServerGenerator):
    def __init__(self, idx, fs, **kwargs):
        self.name = "oss%02d" % idx
        super(OssGenerator, self).__init__(fs, **kwargs)
        self.target_list = [ost for ost in
                            [OstGenerator(host=self.entity, oss_idx=idx, idx=ost_idx, fs=fs, **kwargs)
                                for ost_idx in range(0, kwargs['ost'])]]

class MdtGenerator(TargetGenerator):
    def init_stats(self, **kwargs):
        self.stats = GenStatsDict()
        for idx in range(0, kwargs['ost_stats']):
            stat_name = "mdt_stat_%d" % idx
            self.stats[stat_name] = 0

    def create_entity(self, fs):
        self.entity = ManagedMdt.objects.get_or_create(name=self.name,
                                                       filesystem=fs)[0]
        self.entity.metrics
        super(MdtGenerator, self).create_entity(fs)

    def __init__(self, host, fs, **kwargs):
        self.name = "%s-MDT%04d" % (kwargs['fsname'], 0)
        super(MdtGenerator, self).__init__(host, fs, **kwargs)

class MdsGenerator(ServerGenerator):
    def __init__(self, fs, **kwargs):
        self.name = "mds00"
        super(MdsGenerator, self).__init__(fs, **kwargs)
        self.target_list = [MdtGenerator(host=self.entity, fs=fs, **kwargs)]

class Benchmark(GenericBenchmark):
    def __init__(self, *args, **kwargs):
        self.duration = kwargs['duration']
        self.frequency = kwargs['frequency']
        self.test_runner = DjangoTestSuiteRunner()
        self.prepare(*args, **kwargs)

        settings.USE_FRONTLINE_METRICSTORE = kwargs['use_flms']

    def prepare_oss_list(self, **kwargs):
        return [oss for oss in
                    [OssGenerator(idx=idx, fs=self.fs_entity, **kwargs)
                        for idx in range(0, kwargs['oss'])]]

    def prepare_mds_list(self, **kwargs):
        return [MdsGenerator(fs=self.fs_entity, **kwargs)]

    @transaction.commit_on_success
    def do_db_mangling(self, **kwargs):
        from django.db import connection

        def drop_constraints(cursor, table):
            cursor.execute("SHOW CREATE TABLE %s" % table)
            l = cursor.fetchone()[1].split()
            constraints = [l[i+1] for i in range(0, len(l) - 1) if l[i] == 'CONSTRAINT' and l[i+2] == 'FOREIGN']
            for constraint in constraints:
                cursor.execute("ALTER TABLE %s DROP FOREIGN KEY %s" %
                               (table, constraint.replace('`','')))

        # We need to finagle this by hand since we're not using migrations.
        if kwargs['use_flms'] and kwargs['use_flms_mem']:
            cursor = connection.cursor()
            drop_constraints(cursor, 'monitor_frontlinemetricstore')
            cursor.execute("ALTER TABLE monitor_frontlinemetricstore ENGINE = MEMORY")

        if kwargs['use_r3d_myisam']:
            cursor = connection.cursor()
            for table in "archive cdp cdpprep database datasource pdpprep".split():
                drop_constraints(cursor, "r3d_%s" % table)

            for table in "archive cdp cdpprep database datasource pdpprep".split():
                cursor.execute("ALTER TABLE r3d_%s ENGINE = MYISAM" % table)

    def precreate_stats(self):
        self.stats_list = []
        for i in range(0, self.duration, self.frequency):
            update_servers = []
            for server in self.server_list():
                stats = {'node': {},
                        'lustre': {'target': {}}}
                for node_stat in server.stats.keys():
                    stats['node'][node_stat] = server.stats[node_stat]

                for target in server.target_list:
                    stats['lustre']['target'][target.name] = {}
                    for target_stat in target.stats.keys():
                        stats['lustre']['target'][target.name][target_stat] = target.stats[target_stat]
                update_servers.append([server.entity, stats])

            self.stats_list.append(update_servers)

    def prepare(self, *args, **kwargs):
        from south.management.commands import patch_for_test_db_setup

        self.test_runner.setup_test_environment()
        # This is necessary to ensure that we use django.core.syncdb()
        # instead of south's hacked syncdb()
        patch_for_test_db_setup()
        self.old_db_config = self.test_runner.setup_databases()

        self.do_db_mangling(**kwargs)

        self.mgs = ManagedMgs.objects.create(name="MGS")
        self.fs_entity = ManagedFilesystem.objects.create(name=kwargs['fsname'],
                                                          mgs=self.mgs)
        self.oss_list = self.prepare_oss_list(**kwargs)
        self.mds_list = self.prepare_mds_list(**kwargs)

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
        print "start: %s, stop: %s" % (t2s(run_start),
                                       t2s(run_start + self.duration))
        for update_time in range(int(run_start),
                                 int(run_start + self.duration),
                                 self.frequency):
            sys.stderr.write(t2s(update_time))
            store_start = time.time()
            count = 0

            stats_idx = ((update_time - int(run_start)) / self.frequency)
            for server_stats in self.stats_list[stats_idx]:
                scan.host = server_stats[0]
                scan.host_data = {'metrics': {'raw': server_stats[1]}}
                scan.update_time = update_time
                count += self.store_metrics(scan)

            run_count += count
            store_end = time.time()
            interval = store_end - store_start
            rate = count / interval
            meter = "+" if interval < self.frequency else "-"
            sys.stderr.write(": inserted %d stats (rate: %lf stats/sec) %s\r" % (count, rate, meter))

        run_end = time.time()
        run_interval = run_end - run_start
        run_rate = run_count / run_interval
        print "run count (%d stats) / run time (%lf sec) = run rate (%lf stats/sec)" % (run_count, run_interval, run_rate)

    def cleanup(self):
        self.test_runner.teardown_databases(self.old_db_config)
        self.test_runner.teardown_test_environment()
