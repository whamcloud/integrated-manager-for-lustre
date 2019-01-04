# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import time
import heapq
import collections
from datetime import datetime
from chroma_core.services import log_register
from django.utils.timezone import utc
from chroma_core.models import Point, Series, Stats, ManagedHost, ManagedTarget, ManagedFilesystem
from chroma_core.lib.storage_plugin.api import statistics
from chroma_core.lib import scheduler

metrics_log = log_register("metrics")


class Counter(dict):
    "collections.Counter (builtin in 2.7)"

    def __missing__(self, key):
        return 0

    def update(self, other):
        for key in other:
            self[key] += other[key]


class MetricStore(object):
    """
    Base class for metric stores.
    """

    def __init__(self, measured_object):
        self.measured_object = (
            measured_object.downcast() if hasattr(measured_object, "content_type") else measured_object
        )

    @classmethod
    def new(cls, measured_object):
        "Return downcasted MetricStore based on the type of the measured object."
        for base, cls in [
            (ManagedHost, HostMetricStore),
            (ManagedTarget, TargetMetricStore),
            (ManagedFilesystem, FilesystemMetricStore),
        ]:
            if isinstance(measured_object, base):
                return cls(measured_object)
        raise NotImplementedError

    def serialize(self, update):
        "Generate serialized samples (id, dt, value) from a timestamped update dict."
        for ts, data in update.items():
            dt = datetime.fromtimestamp(ts, utc)
            for name, item in data.items():
                series = Series.get(self.measured_object, name, item["type"])
                yield series.id, dt, item["value"]

    def clear(self):
        "Remove all associated series."
        for series in Series.filter(self.measured_object):
            series.delete()
            Stats.delete(series.id)

    @property
    def names(self):
        "names of all available data series"
        return set(Series.filter(self.measured_object, type__in=Series.DATA_TYPES).values_list("name", flat=True))

    def fetch(self, fetch_metrics, begin, end, max_points=float("inf"), num_points=0):
        "Return datetimes with dicts of field names and values."
        result = collections.defaultdict(dict)
        types = set()
        end = Stats[0].floor(end)  # exclude points from a partial sample
        for series in Series.filter(self.measured_object, name__in=fetch_metrics):
            types.add(series.type)
            minimum = 0.0 if series.type == "Counter" else float("-inf")
            for point in Stats.select(
                series.id, begin, end, rate=series.type in ("Counter", "Derive"), maxlen=max_points, fixed=num_points
            ):
                result[point.dt][series.name] = max(minimum, point.mean)
        # if absolute and derived values are mixed, the earliest value will be incomplete
        if result and types > set(["Gauge"]) and len(result[min(result)]) < len(fetch_metrics):
            del result[min(result)]
        return dict(result)

    def fetch_last(self, fetch_metrics):
        "Return latest datetime and dict of field names and values."
        latest, data = datetime.fromtimestamp(0, utc), {}
        for series in Series.filter(self.measured_object, name__in=fetch_metrics):
            point = Stats.latest(series.id)
            data[series.name] = point.mean
            latest = max(latest, point.dt)
        return latest, data

    def fetch_jobs(self, metric, begin, end, job, max_points=float("inf"), num_points=0):
        "Return datetimes with dicts of field names and values."
        result = collections.defaultdict(dict)
        types = set()
        end = Stats[0].floor(end)  # exclude points from a partial sample
        series_ids = Series.filter(self.measured_object, name__startswith="job_" + metric).values("id")
        series_ids = Stats[0].objects.filter(id__in=series_ids, dt__gte=begin).values("id").distinct("id")
        for series in Series.filter(self.measured_object, id__in=series_ids):
            types.add(series.type)
            for point in Stats.select(series.id, begin, end, rate=True, maxlen=max_points, fixed=num_points):
                result[point.dt][series.name.split("_", 3)[-1]] = point
        assert types.issubset(Series.JOB_TYPES)
        # translate job ids into metadata
        metadata = dict((job_id, job_id) for points in result.values() for job_id in points)
        if job != "id":
            for type in types:  # there should generally be only one
                metadata.update(scheduler.metadata(type, job, metadata))
        for dt in result:
            data = collections.defaultdict(lambda: Point.zero)
            for job_id, point in result[dt].items():
                data[metadata[job_id]] += point
            result[dt] = dict((key, max(0.0, data[key].mean)) for key in data)
        return dict(result)


class VendorMetricStore(MetricStore):
    def serialize(self, stat_name, stat_properties, stat_data):
        "Return serialized samples (id, dt, value) suitable for bulk stats insertion."
        update = {}

        for datapoint in stat_data:
            ts = datapoint["timestamp"]
            val = datapoint["value"]
            if isinstance(stat_properties, statistics.Gauge):
                update[ts] = {stat_name: {"value": val, "type": "Gauge"}}
            elif isinstance(stat_properties, statistics.Counter):
                update[ts] = {stat_name: {"value": val, "type": "Counter"}}
            elif isinstance(stat_properties, statistics.BytesHistogram):
                bins_dict = {}
                for i in range(0, len(val)):
                    bin_stat_name = "%s_%s" % (stat_name, i)
                    bins_dict[bin_stat_name] = {"value": val[i], "type": "Gauge"}
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
            update_time = time.time()

        # Define lists of metrics we care about; ignore everything else.
        mem_included = ["mem_SwapTotal", "mem_SwapFree", "mem_MemFree", "mem_MemTotal"]

        lnet_included = ["lnet_recv_count", "lnet_send_count", "lnet_errors"]

        try:
            for key in metrics["meminfo"]:
                ds_name = "mem_%s" % key
                if not ds_name in mem_included:
                    continue

                update[ds_name] = {"value": metrics["meminfo"][key], "type": "Gauge"}
            for key in metrics["cpustats"]:
                ds_name = "cpu_%s" % key
                update[ds_name] = {"value": metrics["cpustats"][key], "type": "Derive"}
        except KeyError:
            pass

        try:
            for key in metrics["lnet"]:
                ds_name = "lnet_%s" % key
                if not ds_name in lnet_included:
                    continue

                ds_type = "Counter" if "_count" in ds_name else "Gauge"
                ds_type = "Counter" if ds_name == "errors" else ds_type
                update[ds_name] = {"value": metrics["lnet"][key], "type": ds_type}
        except KeyError:
            pass

        return list(MetricStore.serialize(self, {update_time: update}))


class TargetMetricStore(MetricStore):
    """
    Wrapper class for Lustre Target metrics.
    """

    JOB_STATS_LIMIT = 10  # only store the most active jobs

    def serialize(self, metrics, update_time=None, jobid_var="disable"):
        "Return serialized samples (id, dt, value) suitable for bulk stats insertion."
        if update_time is None:
            update_time = time.time()

        stats = metrics.pop("stats", {})
        metrics.pop("brw_stats", None)  # ignore brw_stats
        job_stats = metrics.pop("job_stats", [])
        hsm_stats = metrics.pop("hsm", {})
        update = dict((key, {"value": metrics[key], "type": "Gauge"}) for key in metrics)

        for key in stats:
            ds_name = "stats_%s" % key
            if "sum" in stats[key]:
                if stats[key]["units"] == "reqs":
                    update[ds_name] = {"value": stats[key]["count"], "type": "Counter"}
                elif stats[key]["units"] == "bytes":
                    # Weird one, e.g. OST read_bytes/write_bytes.
                    # We don't want the current value, we want the rate.
                    update[ds_name] = {"value": stats[key]["sum"], "type": "Counter"}
                    update[ds_name.replace("_bytes", "_iops")] = {"value": stats[key]["count"], "type": "Counter"}
                else:
                    update[ds_name] = {"value": stats[key]["sum"], "type": "Gauge"}
            else:
                update[ds_name] = {"value": stats[key]["count"], "type": "Counter"}

        # Let's ignore this for now...  Way too ugh, have a vague idea that
        # this might make sense as a special Datasource type.  Another idea
        # is that we could deconstruct the histograms on the agent side and
        # synthesize a more consolidated representation of the data.  The
        # question is whether or not that consolidation can result in useful
        # data or just entirely destroys the meaning inherent in the
        # histogram representation of the data.
        # for key in brw_stats:
        #    for bucket in brw_stats[key]['buckets']:
        #        for direction in "read write".split():
        #            ds_name = "brw_%s_%s_%s"  % (key, bucket, direction)
        #            update[ds_name] = brw_stats[key]['buckets'][bucket][direction]['count']

        if jobid_var != "disable":
            for stat in heapq.nlargest(
                self.JOB_STATS_LIMIT, job_stats, key=lambda stat: stat["read"]["sum"] + stat["write"]["sum"]
            ):
                # summarize job stats into discrete quantities
                value = sum(
                    stat[key]["samples"] for key in set(stat).difference(["snapshot_time", "read", "write", "job_id"])
                )
                update["job_metadata_iops_{0}".format(stat["job_id"])] = {"value": value, "type": jobid_var}
                for key in ("read", "write"):
                    update["job_{0}_bytes_{1}".format(key, stat["job_id"])] = {
                        "value": stat[key]["sum"],
                        "type": jobid_var,
                    }
                    update["job_{0}_iops_{1}".format(key, stat["job_id"])] = {
                        "value": stat[key]["samples"],
                        "type": jobid_var,
                    }

        for group in hsm_stats:
            for stat in hsm_stats[group]:
                ds_name = "hsm_%s_%s" % (group, stat)
                update[ds_name] = {"value": int(hsm_stats[group][stat]), "type": "Gauge"}

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

    def fetch(self, cfname, query_class, **kwargs):
        raise NotImplementedError("Filesystem-level fetch() not supported!")

    def fetch_last(self, target_class, fetch_metrics):
        """
        Given a target class (ObjectStoreTarget, Metadatatarget, etc),
        and an optional list of desired metrics, returns a tuple
        containing a single row of aggregate datapoints taken
        from each metric's last reading.
        """
        latest, counter = datetime.fromtimestamp(0, utc), Counter()
        for target in target_class.objects.filter(filesystem=self.filesystem):
            dt, data = target.metrics.fetch_last(fetch_metrics)
            counter.update(data)
            latest = max(latest, dt)
        return latest, dict(counter)
