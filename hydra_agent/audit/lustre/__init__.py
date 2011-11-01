import re, os
from hydra_agent.audit import BaseAudit
from hydra_agent.audit.mixins import FileSystemMixin

def local_audit_classes(fscontext=None):
    import hydra_agent.audit.lustre
    return [cls for cls in 
                [getattr(hydra_agent.audit.lustre, name) for name in
                    dir(hydra_agent.audit.lustre) if name.endswith('Audit')]
            if hasattr(cls, 'is_available') and cls.is_available(fscontext)]

class LustreAudit(BaseAudit, FileSystemMixin):
    """Parent class for LustreAudit entities.

    Contains methods which are common to all Lustre cluster component types.
    """
    @classmethod
    def is_available(cls, fscontext=None):
        """Returns a boolean indicating whether or not this audit class should
        be instantiated.
        """
        return (cls.kmod_is_loaded(fscontext) and
                cls.device_is_present(fscontext))

    @classmethod
    def device_is_present(cls, fscontext=None):
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

        obj = cls(fscontext=fscontext)
        entries = [dev for dev in obj.devices() if dev['type'] == modname]
        return len(entries) > 0

    @classmethod
    def kmod_is_loaded(cls, fscontext=None):
        """Returns a boolean indicating whether or not this class'
        corresponding Lustre module is loaded.
        """
        modname = cls.__name__.replace('Audit', '').lower()
        filter = lambda line: line.startswith(modname)
        obj = cls(fscontext=fscontext)
        list = obj.read_lines("/proc/modules", filter)
        return len(list) == 1

    def __init__(self, fscontext=None, **kwargs):
        super(LustreAudit, self).__init__(**kwargs)
        if fscontext:
            self.fscontext = fscontext

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

        return stats

    def dict_from_file(self, file):
        """Creates a dict from simple dict-like (k\s+v) file contents."""
        return dict(re.split('\s+', line) for line in self.read_lines(file))

    def version(self):
        """Returns a string representation of the local Lustre version."""
        stats = self.dict_from_file("/proc/fs/lustre/version")
        return stats["lustre:"]

    def version_info(self):
        """Returns a tuple containing int components of the local Lustre version."""
        return tuple([ int(num) for num in self.version().split('.') ])

    def health_check(self):
        """Returns a string containing Lustre's idea of its own health."""
        return self.read_string("/proc/fs/lustre/health_check")

    def is_healthy(self):
        """Returns a boolean based on our determination of Lustre's health."""
        # NB: Currently we just rely on health_check, but there's no reason
        # we can't extend this to do more. (Perhaps subclass-specific checks?)
        return self.health_check() == "healthy"

    def devices(self):
        """Returns a list of Lustre devices local to this node."""
        try:
            return [{'index': a, 'state': b, 'type': c, 'name': d,
                    'uuid': e, 'refcount': f} for a, b, c, d, e, f in
                [re.split('\s+', line)[1:] for line in
                    self.read_lines('/proc/fs/lustre/devices')]]
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

        self.raw_metrics['lustre']['target'] = {}

    def read_stats(self, target):
        """Returns a dict containing target stats."""
        path = os.path.join(self.target_root, target, "stats")
        return self.stats_dict_from_file(path)

    def read_int_metric(self, target, metric):
        """Given a target name and simple int metric name, returns the
        metric value as an it.  Tries a simple interpolation of the target
        name into the mapped metric path (e.g. osd-ldiskfs/%s/filesfree)
        to allow for complex mappings.

        An IOError will be raised if the metric file cannot be read.
        """
        try:
            mapped_metric = self.int_metric_map[metric] % target
        except TypeError:
            mapped_metric = os.path.join(target, self.int_metric_map[metric])

        path = os.path.join(self.target_root,  mapped_metric)
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
    def __init__(self,**kwargs):
        super(MdsAudit, self).__init__(**kwargs)
        self.target_root = '/proc/fs/lustre/mds'

    def _gather_raw_metrics(self):
        for mdt in [dev for dev in self.devices() if dev['type'] == 'mds']:
            self.raw_metrics['lustre']['target'][mdt['name']] = self.read_int_metrics(mdt['name'])
            self.raw_metrics['lustre']['target'][mdt['name']]['stats'] = self.read_stats(mdt['name'])

class MdtAudit(TargetAudit):
    def __init__(self,**kwargs):
        super(MdtAudit, self).__init__(**kwargs)
        self.target_root = '/proc/fs/lustre'
        self.int_metric_map.update({
            'kbytestotal': 'osd-ldiskfs/%s/kbytestotal',
            'kbytesfree': 'osd-ldiskfs/%s/kbytesfree',
            'filestotal': 'osd-ldiskfs/%s/filestotal',
            'filesfree': 'osd-ldiskfs/%s/filesfree',
            'num_exports': 'mdt/%s/num_exports',
        })

    def read_stats(self, target):
        """Aggregate mish-mash of MDT stats into one stats dict."""
        stats = {}
        for stats_file in "mdt/stats md_stats".split():
            path = os.path.join(self.target_root, "mdt", target, stats_file)
            stats.update(self.stats_dict_from_file(path))
        return stats

    def _gather_raw_metrics(self):
        for mdt in [dev for dev in self.devices() if dev['type'] == 'mdt']:
            self.raw_metrics['lustre']['target'][mdt['name']] = self.read_int_metrics(mdt['name'])
            self.raw_metrics['lustre']['target'][mdt['name']]['stats'] = self.read_stats(mdt['name'])

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
            'I/O time (1/1000s)': 'io_time', # 1000 == CFS_HZ (fingers crossed)
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
        hist_key = None
        for line in self.read_lines(path):
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

    def _gather_raw_metrics(self):
        for ost in [dev for dev in self.devices() if dev['type'] == 'obdfilter']:
            self.raw_metrics['lustre']['target'][ost['name']] = self.read_int_metrics(ost['name'])
            self.raw_metrics['lustre']['target'][ost['name']]['stats'] = self.read_stats(ost['name'])
            self.raw_metrics['lustre']['target'][ost['name']]['brw_stats'] = self.read_brw_stats(ost['name'])

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
