#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import time
import collections
from datetime import datetime
from chroma_core.services import log_register
from django.contrib.contenttypes.models import ContentType
from django.utils.timezone import utc
from chroma_core.models import Series, Stats, ManagedHost, ManagedTarget, ManagedFilesystem
from chroma_core.lib.storage_plugin.api import statistics

metrics_log = log_register('metrics')


class MetricStore(object):
    """
    Base class for metric stores.
    """
    def __init__(self, measured_object):
        self.measured_object = measured_object.downcast() if hasattr(measured_object, 'content_type') else measured_object

    @classmethod
    def new(cls, measured_object):
        "Return downcasted MetricStore based on the type of the measured object."
        for base, cls in [(ManagedHost, HostMetricStore), (ManagedTarget, TargetMetricStore), (ManagedFilesystem, FilesystemMetricStore)]:
            if isinstance(measured_object, base):
                return cls(measured_object)
        raise NotImplementedError

    def _update_time(self):
        """
        Utility method for returning the current time as an int.  Used
        when constructing R3D updates prior to passing them into R3D.
        """
        return int(time.time())

    def serialize(self, update):
        "Generate serialized samples (id, dt, value) from a timestamped update dict."
        for ts, data in update.items():
            dt = datetime.fromtimestamp(ts, utc)
            for name, item in data.items():
                series = Series.get(self.measured_object, name, item['type'])
                yield series.id, dt, item['value']

    def clear(self):
        "Remove all associated series."
        ct = ContentType.objects.get_for_model(self.measured_object)
        for series in Series.objects.filter(content_type=ct, object_id=self.measured_object.id):
            series.delete()
            Stats.delete(series.id)

    def series(self, *names):
        "Generate existing series by name for this source."
        for name in names:
            try:
                yield Series.get(self.measured_object, name)
            except Series.DoesNotExist:
                pass

    def fetch(self, cfname, fetch_metrics, start_time, end_time, max_points=1000, **kwargs):
        "Return ordered timestamps, dicts of field names and values."
        assert cfname == 'Average', cfname
        result = collections.defaultdict(dict)
        types = set()
        for series in self.series(*fetch_metrics):
            types.add(series.type)
            for point in Stats.select(series.id, start_time, end_time, rate=series.type in ('Counter', 'Derive'), maxlen=max_points):
                result[point.timestamp][series.name] = point.mean
        # if absolute and derived values are mixed, the earliest value will be incomplete
        if result and types > set(['Gauge']) and len(result[min(result)]) < len(fetch_metrics):
            del result[min(result)]
        return sorted(result.items())

    def fetch_last(self, fetch_metrics=()):
        "Return latest timestamp and dict of field names and values."
        timestamp, result = 0, {}
        for series in self.series(*fetch_metrics):
            point = Stats.latest(series.id)
            result[series.name] = point.mean
            timestamp = max(timestamp, point.timestamp)
        return timestamp, result


class VendorMetricStore(MetricStore):

    def serialize(self, stat_name, stat_properties, stat_data):
        "Return serialized samples (id, dt, value) suitable for bulk stats insertion."
        update = {}

        for datapoint in stat_data:
            ts = datapoint['timestamp']
            val = datapoint['value']
            if isinstance(stat_properties, statistics.Gauge):
                update[ts] = {stat_name: {'value': val, 'type': 'Gauge'}}
            elif isinstance(stat_properties, statistics.Counter):
                update[ts] = {stat_name: {'value': val, 'type': 'Counter'}}
            elif isinstance(stat_properties, statistics.BytesHistogram):
                bins_dict = {}
                for i in range(0, len(val)):
                    bin_stat_name = "%s_%s" % (stat_name, i)
                    bins_dict[bin_stat_name] = {'value': val[i], 'type': 'Gauge'}
                update[ts] = bins_dict

        return list(MetricStore.serialize(self, update))


class HostMetricStore(MetricStore):
    """
    Wrapper class for ManagedHost metrics.
    """
    def serialize(self, metrics, update_time=None):
        "Return serialized samples (id, dt, value) suitable for bulk stats insertion."
        update = {}
        if update_time is None:
            update_time = self._update_time()

        # Define lists of metrics we care about; ignore everything else.
        mem_included = ['mem_SwapTotal',
                        'mem_SwapFree',
                        'mem_MemFree',
                        'mem_MemTotal']

        lnet_included = ["lnet_recv_count",
                         "lnet_send_count",
                         "lnet_errors"]

        try:
            for key in metrics['meminfo']:
                ds_name = "mem_%s" % key
                if not ds_name in mem_included:
                    continue

                update[ds_name] = {'value': metrics['meminfo'][key],
                                   'type': 'Gauge'}
            for key in metrics['cpustats']:
                ds_name = "cpu_%s" % key
                update[ds_name] = {'value': metrics['cpustats'][key],
                                   'type': 'Derive'}
        except KeyError:
            pass

        try:
            for key in metrics['lnet']:
                ds_name = "lnet_%s" % key
                if not ds_name in lnet_included:
                    continue

                ds_type = "Counter" if "_count" in ds_name else "Gauge"
                ds_type = "Counter" if ds_name == "errors" else ds_type
                update[ds_name] = {'value': metrics['lnet'][key],
                                   'type': ds_type}
        except KeyError:
            pass

        return list(MetricStore.serialize(self, {update_time: update}))


class TargetMetricStore(MetricStore):
    """
    Wrapper class for Lustre Target metrics.
    """
    def serialize(self, metrics, update_time=None):
        "Return serialized samples (id, dt, value) suitable for bulk stats insertion."
        update = {}
        if update_time is None:
            update_time = self._update_time()

        stats = {}
        #brw_stats = {}
        for key in metrics:
            if key == "stats":
                stats = metrics[key]
            elif key == "brw_stats":
                pass
                #brw_stats = metrics[key]
            else:
                update[key] = {'value': metrics[key], 'type': 'Gauge'}

        for key in stats:
            ds_name = "stats_%s" % key
            if "sum" in stats[key]:
                if stats[key]['units'] == "reqs":
                    update[ds_name] = {'value': stats[key]['count'],
                                       'type': 'Counter'}
                elif stats[key]['units'] == "bytes":
                    # Weird one, e.g. OST read_bytes/write_bytes.
                    # We don't want the current value, we want the rate.
                    update[ds_name] = {'value': stats[key]['sum'],
                                       'type': 'Counter'}
                else:
                    update[ds_name] = {'value': stats[key]['sum'],
                                       'type': 'Gauge'}
            else:
                update[ds_name] = {'value': stats[key]['count'],
                                   'type': 'Counter'}

        # Let's ignore this for now...  Way too ugh, have a vague idea that
        # this might make sense as a special Datasource type.  Another idea
        # is that we could deconstruct the histograms on the agent side and
        # synthesize a more consolidated representation of the data.  The
        # question is whether or not that consolidation can result in useful
        # data or just entirely destroys the meaning inherent in the
        # histogram representation of the data.
        #for key in brw_stats:
        #    for bucket in brw_stats[key]['buckets']:
        #        for direction in "read write".split():
        #            ds_name = "brw_%s_%s_%s"  % (key, bucket, direction)
        #            update[ds_name] = brw_stats[key]['buckets'][bucket][direction]['count']

        return list(MetricStore.serialize(self, {update_time: update}))


class FilesystemMetricStore(MetricStore):
    """
    Wrapper class for Filesystem-level aggregate metrics.  Read-only.
    """
    def __init__(self, managed_object, *args, **kwargs):
        # Override the parent __init__(), as we don't need an R3D for
        # a Filesystem.
        self.filesystem = managed_object

    def serialize(self, *args, **kwargs):
        """Don't use this -- will raise a NotImplementedError!"""
        raise NotImplementedError("Filesystem-level serialize() not supported!")

    def list(self, query_class):
        """
        list(query_class)

        Given a query class (ManagedOst, ManagedMst, ManagedHost, etc.),
        returns a dict of metric name:type pairs found in all target metrics.
        """
        metrics = {}

        from django.core.exceptions import FieldError
        try:
            fs_components = query_class.objects.filter(filesystem=self.filesystem)
        except FieldError:
            if query_class.__name__ == "ManagedHost":
                fs_components = self.filesystem.get_servers()
            else:
                raise NotImplementedError("Unknown query class: %s" % query_class.__name__)

        for comp in fs_components:
            metrics.update(comp.metrics.list())

        return metrics

    def fetch(self, cfname, query_class, **kwargs):
        """
        fetch(CFNAME, query_class [, fetch_metrics=['name'],
                      start_time=datetime, end_time=datetime])

        Given a consolidation function (Average, Min, Max, Last),
        a query class (ManagedOst, ManagedMdt, ManagedHost, etc.)
        an optional list of desired metrics, an optional start time,
        and an optinal end time, returns a tuple containing rows of
        aggregate datapoints retrieved from the appropriate RRAs.
        """
        results = {}

        from django.core.exceptions import FieldError
        try:
            fs_components = query_class.objects.filter(filesystem=self.filesystem)
        except FieldError:
            if query_class.__name__ == "ManagedHost":
                fs_components = self.filesystem.get_servers()
            else:
                raise NotImplementedError("Unknown query class: %s" % query_class.__name__)

        for fs_component in fs_components:
            for row in fs_component.metrics.fetch(cfname, **kwargs):
                row_ts = row[0]
                row_dict = row[1]

                if not row_ts in results:
                    results[row_ts] = {}

                for metric in row_dict.keys():
                    try:
                        if row_dict[metric] is not None:
                            if results[row_ts][metric] is None:
                                results[row_ts][metric] = row_dict[metric]
                            else:
                                results[row_ts][metric] += row_dict[metric]
                    except KeyError:
                        results[row_ts][metric] = row_dict[metric]

        return tuple(
                sorted(
                    [(timestamp, dict) for (timestamp, dict)
                                        in results.items()],
                                        key=lambda timestamp: timestamp
                )
        )

    def fetch_last(self, target_class, fetch_metrics=None):
        """
        fetch_last(target_class [, fetch_metrics=['metric']])

        Given a target class (ObjectStoreTarget, Metadatatarget, etc),
        and an optional list of desired metrics, returns a tuple
        containing a single row of aggregate datapoints taken
        from each metric's last reading.
        """
        results = []

        for target in target_class.objects.filter(filesystem=self.filesystem):
            tm = target.metrics.fetch_last(fetch_metrics)

            # Bit of a hack here -- deal semi-gracefully with the possibility
            # that different targets might have different times for their
            # last update by just using the most recent.
            try:
                results[0] = tm[0] if tm[0] > results[0] else results[0]
            except IndexError:
                results.append(tm[0])
                results.append({})

            for metric in tm[1].keys():
                try:
                    if tm[1][metric] is None:
                        results[1][metric] += 0
                    else:
                        results[1][metric] += tm[1][metric]
                except KeyError:
                    results[1][metric] = tm[1][metric]

        return tuple(results)
