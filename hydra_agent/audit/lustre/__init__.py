import re, os
from hydra_agent.audit import BaseAudit
from hydra_agent.context import Context
from hydra_agent.audit.mixins import FileSystemMixin

def local_audit_classes(context=Context()):
    import hydra_agent.audit.lustre
    return [cls for cls in 
                [getattr(hydra_agent.audit.lustre, name)
                    for name in dir(hydra_agent.audit.lustre)
                        if name.endswith('Audit') and name is not 'LustreAudit']
            if hasattr(cls, 'kmod_is_loaded') and cls.kmod_is_loaded(context)]

class LustreAudit(BaseAudit, FileSystemMixin):
    """Parent class for LustreAudit entities.

    Contains methods which are common to all Lustre cluster component types.
    """
    @classmethod
    def kmod_is_loaded(cls, context=Context()):
        """Returns a boolean based whether or not this class' corresponding Lustre module is loaded."""
        modname = cls.__name__.replace('Audit', '').lower()
        filter = lambda line: line.startswith(modname)
        obj = cls()
        obj.context = context
        list = obj.read_lines("/proc/modules", filter)
        return len(list) == 1

    def __init__(self):
        super(LustreAudit, self).__init__()
        from collections import defaultdict
        self.raw_metrics['lustre'] = defaultdict(lambda: defaultdict(lambda: defaultdict()))

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
        return [{'index': a, 'state': b, 'type': c, 'name': d,
                 'uuid': e, 'refcount': f} for a, b, c, d, e, f in
            [re.split('\s+', line)[1:] for line in
                self.read_lines('/proc/fs/lustre/devices')]]
   
    def _gather_raw_metrics(self):
        raise NotImplementedError

    def metrics(self):
        """Returns a hash of metric values."""
        self._gather_raw_metrics()
        return {"raw": self.raw_metrics}

class TargetAudit(LustreAudit):
    def __init__(self):
        super(TargetAudit, self).__init__()
        self.int_metric_map = {
            'kbytestotal': 'kbytestotal',
            'kbytesfree': 'kbytesfree',
            'kbytesavail': 'kbytesavail',
            'filestotal': 'filestotal',
            'filesfree': 'filesfree',
            'num_exports': 'num_exports'
        }

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

class MdtAudit(TargetAudit):
    def __init__(self):
        super(MdtAudit, self).__init__()
        self.target_root = '/proc/fs/lustre'
        self.int_metric_map.update({
            'kbytestotal': 'osd-ldiskfs/%s/kbytestotal',
            'kbytesfree': 'osd-ldiskfs/%s/kbytesfree',
            'filestotal': 'osd-ldiskfs/%s/filestotal',
            'filesfree': 'osd-ldiskfs/%s/filesfree',
            'num_exports': 'mdt/%s/num_exports',
        })

    def _gather_raw_metrics(self):
        for mdt in [dev for dev in self.devices() if dev['type'] == 'mdt']:
            self.raw_metrics['lustre']['target'][mdt['name']] = self.read_int_metrics(mdt['name'])

class MgsAudit(TargetAudit):
    def __init__(self):
        super(MgsAudit, self).__init__()
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
    def __init__(self):
        super(ObdfilterAudit, self).__init__()
        self.target_root = '/proc/fs/lustre/obdfilter'
        self.int_metric_map.update({
            'tot_dirty': 'tot_dirty',
            'tot_granted': 'tot_granted',
            'tot_pending': 'tot_pending'
        })

    def _gather_raw_metrics(self):
        for ost in [dev for dev in self.devices() if dev['type'] == 'obdfilter']:
            self.raw_metrics['lustre']['target'][ost['name']] = self.read_int_metrics(ost['name'])
            self.raw_metrics['lustre']['target'][ost['name']]['stats'] = self.read_stats(ost['name'])

class LnetAudit(LustreAudit):
    def parse_lnet_stats(self):
        stats_str = self.read_string('/proc/sys/lnet/stats')
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
