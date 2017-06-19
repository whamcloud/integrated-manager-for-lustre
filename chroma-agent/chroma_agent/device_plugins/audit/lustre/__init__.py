# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import re
import os
import heapq
from collections import defaultdict
from collections import namedtuple

from tablib.packages import yaml
from chroma_agent.utils import Mounts
from chroma_agent.device_plugins.audit import BaseAudit
from chroma_agent.device_plugins.audit.mixins import FileSystemMixin


# HYD-2307 workaround
DISABLE_BRW_STATS = True
JOB_STATS_LIMIT = 20  # only return the most active jobs


def local_audit_classes():
    import chroma_agent.device_plugins.audit.lustre
    return [cls for cls in
            [getattr(chroma_agent.device_plugins.audit.lustre, name) for name in
             dir(chroma_agent.device_plugins.audit.lustre) if name.endswith('Audit')]
            if hasattr(cls, 'is_available') and cls.is_available()]


class LustreAudit(BaseAudit, FileSystemMixin):
    """Parent class for LustreAudit entities.

    Contains methods which are common to all Lustre cluster component types.
    """

    LustreVersion = namedtuple('LustreVersion', ['major', 'minor', 'patch'])

    @classmethod
    def is_available(cls):
        """Returns a boolean indicating whether or not this audit class should
        be instantiated.
        """
        return (cls.kmod_is_loaded() and
                cls.device_is_present())

    @classmethod
    def device_is_present(cls):
        """Returns a boolean indicating whether or not this class
        has any corresponding Lustre device entries.
        """
        modname = cls.__name__.replace('Audit', '').lower()

        # There are some modules which can be loaded but don't have
        # corresponding device entries.  In these cases, just wink and
        # move on.
        exceptions = "lnet".split()
        if modname in exceptions:
            return True

        obj = cls()
        entries = [dev for dev in obj.devices() if dev['type'] == modname]
        return len(entries) > 0

    @classmethod
    def kmod_is_loaded(cls):
        """Returns a boolean indicating whether or not this class'
        corresponding Lustre module is loaded.
        """
        modname = cls.__name__.replace('Audit', '').lower()

        def filter(line):
            return line.startswith(modname)

        obj = cls()
        try:
            modules = list(obj.read_lines("/proc/modules", filter))
        except IOError:
            modules = []

        return len(modules) == 1

    def __init__(self, **kwargs):
        super(LustreAudit, self).__init__(**kwargs)

        self.raw_metrics['lustre'] = {}

    def stats_dict_from_file(self, file):
        """Creates a dict from Lustre stats file contents."""
        stats_re = re.compile(r"""
        # e.g.
        # create                    726 samples [reqs]
        # cache_miss                21108 samples [pages] 1 1 21108
        # obd_ping                  1108 samples [usec] 15 72 47014 2156132
        ^
        (?P<name>\w+)\s+(?P<count>\d+)\s+samples\s+\[(?P<units>\w+)\]
        (?P<min_max_sum>\s+(?P<min>\d+)\s+(?P<max>\d+)\s+(?P<sum>\d+)
        (?P<sumsq>\s+(?P<sumsquare>\d+))?)?
        $
        """, re.VERBOSE)

        stats = {}

        # There is a potential race between the time that an OBD module
        # is loaded and the stats entry is created (HYD-389).  If we read
        # during that window, the audit will crash.  I'm not crazy about
        # excepting IOErrors as a general rule, but I suppose this is
        # the least-worst solution.
        try:
            for line in self.read_lines(file):
                match = re.match(stats_re, line)
                if not match:
                    continue

                name = match.group('name')
                stats[name] = {
                    'count': int(match.group('count')),
                    'units': match.group('units')
                }
                if match.group("min_max_sum") is not None:
                    stats[name].update({
                        'min': int(match.group('min')),
                        'max': int(match.group('max')),
                        'sum': int(match.group('sum'))
                    })
                if match.group("sumsq") is not None:
                    stats[name].update({
                        'sumsquare': int(match.group('sumsquare'))
                    })
        except IOError:
            return stats

        return stats

    def dict_from_file(self, file):
        """Creates a dict from simple dict-like (k\s+v) file contents."""
        return dict(re.split('\s+', line) for line in self.read_lines(file))

    @property
    def version(self):
        """Returns a string representation of the local Lustre version."""
        try:
            return self.read_string("/sys/fs/lustre/version")
        except IOError:
            return "0.0.0"

    @property
    def version_info(self):
        """Returns a LustreVersion containing major, minor and patch components of the local Lustre version."""
        result = []

        for element in (self.version.split('.') + ['0', '0', '0'])[0:3]:
            digits = re.match('\d+', element)

            if digits:
                result.append(int(digits.group()))
            else:
                result.append(0)

        return self.LustreVersion(*result)

    def health_check(self):
        """Returns a string containing Lustre's idea of its own health."""
        return self.read_string("/sys/fs/lustre/health_check")

    def is_healthy(self):
        """Returns a boolean based on our determination of Lustre's health."""
        # NB: Currently we just rely on health_check, but there's no reason
        # we can't extend this to do more. (Perhaps subclass-specific checks?)
        return self.health_check() == "healthy"

    def devices(self):
        """Returns a list of Lustre devices local to this node."""
        try:
            return [dict(zip(['index', 'state', 'type', 'name',
                              'uuid', 'refcount'], line.split()))
                    for line in self.read_lines('/sys/kernel/debug/lustre/devices')]
        except IOError:
            return []

    def _gather_raw_metrics(self):
        raise NotImplementedError

    def metrics(self):
        """Returns a hash of metric values."""
        self._gather_raw_metrics()
        return {"raw": self.raw_metrics}


class TargetAudit(LustreAudit):
    def __init__(self, **kwargs):
        super(TargetAudit, self).__init__(**kwargs)
        self.int_metric_map = {
            'kbytestotal': 'kbytestotal',
            'kbytesfree': 'kbytesfree',
            'kbytesavail': 'kbytesavail',
            'filestotal': 'filestotal',
            'filesfree': 'filesfree',
            'num_exports': 'num_exports'
        }
        self.metric_defaults_map = {
            'read_bytes': dict(count = 0, units = "bytes", min = 0, max = 0, sum = 0),
            'write_bytes': dict(count = 0, units = "bytes", min = 0, max = 0, sum = 0),
        }

        self.raw_metrics['lustre']['target'] = {}

    def read_stats(self, target):
        """Returns a dict containing target stats."""
        path = os.path.join(self.target_root, target, "stats")
        stats = self.stats_dict_from_file(path)

        # Check for missing stats that need default values.
        for stat, default in self.metric_defaults_map.items():
            if stat not in stats:
                stats[stat] = default

        return stats

    def read_int_metric(self, target, metric):
        """Given a target name and simple int metric name, returns the
        metric value as an int.  Tries a simple interpolation of the target
        name into the mapped metric path (e.g. osd-ldiskfs/%s/filesfree)
        to allow for complex mappings.

        An IOError will be raised if the metric file cannot be read.
        """
        try:
            mapped_metric = self.int_metric_map[metric] % target
        except TypeError:
            mapped_metric = os.path.join(target, self.int_metric_map[metric])

        path = os.path.join(self.target_root, mapped_metric)
        return self.read_int(path)

    def read_int_metrics(self, target):
        """Given a target name, returns a hash of simple int metrics
        found for that target (e.g. filesfree).
        """
        metrics = {}
        for metric in self.int_metric_map.keys():
            try:
                metrics[metric] = self.read_int_metric(target, metric)
            except IOError:
                # Don't bomb on missing metrics, just skip 'em.
                pass

        return metrics


class MdsAudit(TargetAudit):
    """In Lustre < 2.x, the MDT stats were mis-named as MDS stats."""
    @classmethod
    def is_available(cls):
        """Stupid override to prevent this being used on 2.x+ filesystems."""
        if cls().version_info.major < 2:
            return super(MdsAudit, cls).is_available()
        else:
            return False

    def __init__(self, **kwargs):
        super(MdsAudit, self).__init__(**kwargs)
        self.target_root = '/proc/fs/lustre/mds'

    def _gather_raw_metrics(self):
        for mdt in [dev for dev in self.devices() if dev['type'] == 'mds']:
            self.raw_metrics['lustre']['target'][mdt['name']] = self.read_int_metrics(mdt['name'])
            self.raw_metrics['lustre']['target'][mdt['name']]['stats'] = self.read_stats(mdt['name'])


class MdtAudit(TargetAudit):
    def __init__(self, **kwargs):
        super(MdtAudit, self).__init__(**kwargs)
        self.target_root = '/proc/fs/lustre'
        self.int_metric_map.update({
            'kbytestotal': 'osd-ldiskfs/%s/kbytestotal',
            'kbytesfree': 'osd-ldiskfs/%s/kbytesfree',
            'filestotal': 'osd-ldiskfs/%s/filestotal',
            'filesfree': 'osd-ldiskfs/%s/filesfree',
        })

    def _parse_hsm_agent_stats(self, stats_root):
        stats = {
            'total': 0,
            'idle': 0,
            'busy': 0
        }

        for line in self.read_lines(os.path.join(stats_root, "agents")):
            # uuid=... archive_id=1 requests=[current:0 ok:1 errors:0]
            stats['total'] += 1
            if 'current:0' in line:
                stats['idle'] += 1
            else:
                stats['busy'] += 1

        return stats

    def _parse_hsm_action_stats(self, stats_root):
        stats = {
            'waiting': 0,
            'running': 0,
            'succeeded': 0,
            'errored': 0
        }

        for line in self.read_lines(os.path.join(stats_root, "actions")):
            if 'status=WAITING' in line:
                stats['waiting'] += 1
            elif 'status=SUCCEED' in line:
                stats['succeeded'] += 1
            elif 'status=STARTED' in line:
                stats['running'] += 1

        return stats

    def get_hsm_stats(self, target):
        control_file = os.path.join(self.target_root, "mdt",
                                    target, "hsm_control")
        try:
            if self.read_string(control_file) != "enabled":
                return {}
        except IOError:
            return {}

        stats_root = os.path.join(self.target_root, "mdt", target, "hsm")
        agent_stats = self._parse_hsm_agent_stats(stats_root)
        action_stats = self._parse_hsm_action_stats(stats_root)
        return {
            'agents': agent_stats,
            'actions': action_stats
        }

    def read_stats(self, target):
        """
        Aggregate mish-mash of MDT stats into one stats dict.

        As of lustre version 2.9.58, some of the expected stats have moved to /proc/fs/lustre/mds/MDS/mdt
        """
        stats = {}
        for stats_file in ["mdt/%s/md_stats" % target, "mds/MDS/mdt/stats"]:
            path = os.path.join(self.target_root, stats_file)
            stats.update(self.stats_dict_from_file(path))

        return stats

    def get_client_count(self, target):
        """The target is expected to be of the format $fs_name-MDTXXXX.  example
           lustre-MDT0000.  The directory passed is expected to have a set of
           subdirs, one per remote nid and one for the local nid.  In each of
           these subdirs there should be a uuid file.  This uuid can contain
           2 types of entries for the different types of connections to the MDT:
             1. for MDT or OST.  Ex:
                lustre-MDT0000-lwp-MDT0000_UUID
                lustre-MDT0003-mdtlov_UUID
                lustre-MDT0000-lwp-OST0001_UUID
             2. For actual clients connected.  Ex:
                ef9b5ecf-b9c1-110c-199a-ea910b02d998
          This function finds the second type of entries and counts those as
          clients."""
        count = 0
        fs_name = target[:target.rfind("MDT")]
        rootdir = os.path.join(self.target_root, "mdt", target, "exports")
        for subdir, dirs, files in self.walk(rootdir):
            for f in files:
                if f == "uuid":
                    uuid = os.path.join(rootdir, os.path.basename(subdir), f)
                    for line in self.read_lines(uuid):
                        if line and line.find(fs_name + "MDT") < 0:
                            count = count + 1
        return count

    def _gather_raw_metrics(self):
        for mdt in [dev for dev in self.devices() if dev['type'] == 'mdt']:
            self.raw_metrics['lustre']['target'][mdt['name']] = self.read_int_metrics(mdt['name'])
            try:
                self.raw_metrics['lustre']['target'][mdt['name']]['client_count'] = self.get_client_count(mdt['name'])
            except KeyError:
                pass
            self.raw_metrics['lustre']['target'][mdt['name']]['stats'] = self.read_stats(mdt['name'])
            self.raw_metrics['lustre']['target'][mdt['name']]['hsm'] = self.get_hsm_stats(mdt['name'])


class MgsAudit(TargetAudit):
    def __init__(self, **kwargs):
        super(MgsAudit, self).__init__(**kwargs)
        self.target_root = '/proc/fs/lustre/mgs'
        self.int_metric_map.update({
            'num_exports': 'num_exports',
            'threads_started': 'mgs/threads_started',
            'threads_min': 'mgs/threads_min',
            'threads_max': 'mgs/threads_max',
        })

    def read_stats(self, target):
        """Returns a dict containing MGS stats."""
        path = os.path.join(self.target_root, target, "mgs/stats")
        return self.stats_dict_from_file(path)

    def _gather_raw_metrics(self):
        self.raw_metrics['lustre']['target']['MGS'] = self.read_int_metrics('MGS')
        self.raw_metrics['lustre']['target']['MGS']['stats'] = self.read_stats('MGS')


class ObdfilterAudit(TargetAudit):
    def __init__(self, **kwargs):
        super(ObdfilterAudit, self).__init__(**kwargs)
        self.target_root = '/proc/fs/lustre/obdfilter'
        self.int_metric_map.update({
            'tot_dirty': 'tot_dirty',
            'tot_granted': 'tot_granted',
            'tot_pending': 'tot_pending'
        })
        self.job_stat_last_snapshot_time = defaultdict(int)

    def read_brw_stats(self, target):
        """Return a dict representation of an OST's brw_stats histograms."""
        histograms = {}

        # I know these hist names are fugly, but they match the names in the
        # Lustre source.  When possible, we should retain Lustre names
        # for things to make life easier for archaeologists.
        hist_map = {
            'pages per bulk r/w': 'pages',
            'discontiguous pages': 'discont_pages',
            'discontiguous blocks': 'discont_blocks',
            'disk fragmented I/Os': 'dio_frags',
            'disk I/Os in flight': 'rpc_hist',
            'I/O time (1/1000s)': 'io_time',  # 1000 == CFS_HZ (fingers crossed)
            'disk I/O size': 'disk_iosize'
        }

        header_re = re.compile("""
        # e.g.
        # disk I/O size          ios   % cum % |  ios   % cum %
        # discontiguous blocks   rpcs  % cum % |  rpcs  % cum %
        ^(?P<name>.+?)\s+(?P<units>\w+)\s+%
        """, re.VERBOSE)

        bucket_re = re.compile("""
        # e.g.
        # 0:               187  87  87   | 13986  91  91
        # 128K:            784  76 100   | 114654  82 100
        ^
        (?P<name>[\w]+):\s+
        (?P<read_count>\d+)\s+(?P<read_pct>\d+)\s+(?P<read_cum_pct>\d+)
        \s+\|\s+
        (?P<write_count>\d+)\s+(?P<write_pct>\d+)\s+(?P<write_cum_pct>\d+)
        $
        """, re.VERBOSE)

        path = os.path.join(self.target_root, target, "brw_stats")
        try:
            lines = self.read_lines(path)
        except IOError:
            return histograms

        hist_key = None
        for line in lines:
            header = re.match(header_re, line)
            if header is not None:
                hist_key = hist_map[header.group('name')]
                histograms[hist_key] = {}
                histograms[hist_key]['units'] = header.group('units')
                histograms[hist_key]['buckets'] = {}
                continue

            bucket = re.match(bucket_re, line)
            if bucket is not None:
                assert hist_key is not None

                name = bucket.group('name')
                bucket_vals = {
                    'read': {
                        'count': int(bucket.group('read_count')),
                        'pct': int(bucket.group('read_pct')),
                        'cum_pct': int(bucket.group('read_cum_pct'))
                    },
                    'write': {
                        'count': int(bucket.group('write_count')),
                        'pct': int(bucket.group('write_pct')),
                        'cum_pct': int(bucket.group('write_cum_pct'))
                    }
                }
                histograms[hist_key]['buckets'][name] = bucket_vals

        return histograms

    def _read_job_stats_yaml_file(self, target_name):
        """Given a path to a yaml file, read the file into a dict and return a value

        return values will be an list or None.
        If an list, it will hold the parsed stats as a list from the job_stats file, could be an empty list
        If None, callers can conclude job stats is not turned on.

        The main value of splitting this is so it can be mocked out in tests.

        :param path  Full path to the yaml file (i.e. /proc/fs/lustre/obdfilter/lustre-OST0000/job_stats)

        Sample Code showing the output when job stats is cleared.
        $ lctl set_param obdfilter.*.job_stats=clear
        >>> from tablib.packages import yaml
        >>> f = open('/proc/fs/lustre/obdfilter/ldiskfs-OST0001/job_stats')
        >>> d = yaml.load(f)
        >>> d.items()
        [('job_stats', None)]

        """
        path = self.abs(os.path.join(self.target_root, target_name, 'job_stats'))
        try:
            with open(path) as yaml_file:
                read_dict = yaml.load(yaml_file)
        except IOError:
            # If job stats is NOT turned on, the file will not exist
            return None
        else:
            # job stats output should always have this key, but it will return None when there are not stats
            # Instead this method should return [].  None means job stats is not turned on.
            return read_dict.get("job_stats") or []

    def read_job_stats(self, target_name):
        """Try to read and return the contents of /proc/fs/lustre/obdfilter/<target>/job_stats

        Attempt to read the proc file, parse, and find up to the top few jobs in the report
        ranked by "write.sum" + "read.sum"

        Only return newly found job stats as determined by snapshot time provided by Lustre in the job_stats proc file.
        In an active system, this ought to give meaning results, while in a quiet system, the top X stats may
        all be zero, or some other equal value from sample to sample, and therefore be supressed.

        If Job stats is not turned on, there will be no proc file path, and this method will return [] as if no stats
        are found.
        """

        stats = self._read_job_stats_yaml_file(target_name)

        if not stats:
            # stats is None when job stats is disabled, or [] if enabled but empty
            # currently no reason it differentiate, so return as if empty
            return []

        #  Initialize this dict in preparation to collect just these latest snapshot times as seen in this stats sample
        latest_job_stat_snapshot_times = defaultdict(int)

        stats_to_return = []
        for stat in stats:
            # Convert to a format expected in other parts of the application.
            stat['read'] = stat.pop('read_bytes')
            stat['write'] = stat.pop('write_bytes')

            #  Record that we know about this stat
            latest_job_stat_snapshot_times[stat['job_id']] = stat['snapshot_time']

            #  if we knew about this last run, and the time is new, then report it
            if self.job_stat_last_snapshot_time[stat['job_id']] < stat['snapshot_time']:
                stats_to_return.append(stat)

        #  The local dict will have all the current times for jobs we are tracking, so update the instance copy.
        self.job_stat_last_snapshot_time = latest_job_stat_snapshot_times

        #  Get the top few job stats based on read+write sum.
        return heapq.nlargest(JOB_STATS_LIMIT, stats_to_return, key=lambda stat: stat['read']['sum'] + stat['write']['sum'])

    def _gather_raw_metrics(self):
        metrics = self.raw_metrics['lustre']
        try:
            metrics['jobid_var'] = self.read_string('/sys/fs/lustre/jobid_var')
        except IOError:
            metrics['jobid_var'] = 'disable'
        for ost in [dev for dev in self.devices() if dev['type'] == 'obdfilter']:
            metrics['target'][ost['name']] = self.read_int_metrics(ost['name'])
            metrics['target'][ost['name']]['stats'] = self.read_stats(ost['name'])
            if not DISABLE_BRW_STATS:
                metrics['target'][ost['name']]['brw_stats'] = self.read_brw_stats(ost['name'])
            metrics['target'][ost['name']]['job_stats'] = self.read_job_stats(ost['name'])


class OstAudit(ObdfilterAudit):
    @classmethod
    def is_available(cls):
        # Not pretty, but it works. On 2.4+, the ost module is loaded,
        # but the obdfilter module is not. Pre-2.4, both are loaded, so
        # we need to prevent double audits. Really, this whole method of
        # determining which audits to run needs to be reworked. Later.
        lustre_version = cls().version_info
        if lustre_version.major < 2:
            return False
        elif (lustre_version.major == 2) and (lustre_version.minor < 4):
            return False
        else:
            return super(OstAudit, cls).is_available()


class LnetAudit(LustreAudit):
    def parse_lnet_stats(self):
        try:
            stats_str = self.read_string('/proc/sys/lnet/stats')
        except IOError:
            # Normally, this would be an exceptional condition, but in
            # the case of lnet, it could happen when the module is loaded
            # but lnet is not configured.
            return {}

        (a, b, c, d, e, f, g, h, i, j, k) = [int(v) for v in
                                             re.split('\s+', stats_str)]
        # lnet/lnet/router_proc.c
        return {'msgs_alloc': a, 'msgs_max': b,
                'errors': c,
                'send_count': d, 'recv_count': e,
                'route_count': f, 'drop_count': g,
                'send_length': h, 'recv_length': i,
                'route_length': j, 'drop_length': k}

    def _gather_raw_metrics(self):
        self.raw_metrics['lustre']['lnet'] = self.parse_lnet_stats()


class ClientAudit(LustreAudit):
    """
    Audit Lustre client information. Included in audit payload when
    a mounted Lustre client is detected.
    """
    @classmethod
    def is_available(cls):
        return len(cls._client_mounts())

    @classmethod
    def _client_mounts(cls):
        spec = re.compile(r'@\w+:/\w+')
        # Mounts().all() returns a list of tuples in which the third element
        # is the filesystem type.
        return [mount for mount in Mounts().all()
                if mount[2] == 'lustre' and spec.search(mount[0])]

    def _gather_raw_metrics(self):
        client_mounts = []
        for mount in self.__class__._client_mounts():
            client_mounts.append(dict(mountspec = mount[0],
                                      mountpoint = mount[1]))

        self.raw_metrics['lustre_client_mounts'] = client_mounts
