import re, math
from django.contrib.contenttypes.models import ContentType
from r3d.models import *

import settings
import logging
metrics_log = logging.getLogger('metrics')
metrics_log.setLevel(logging.DEBUG)
handler = logging.FileHandler(settings.JOB_LOG_PATH)
handler.setFormatter(logging.Formatter('[%(asctime)s] %(message)s',
                                       '%d/%b/%Y:%H:%M:%S'))
metrics_log.addHandler(handler)
if settings.DEBUG:
    metrics_log.setLevel(logging.DEBUG)
    metrics_log.addHandler(logging.StreamHandler())
else:
    metrics_log.setLevel(logging.INFO)

class MetricStore(object):
    """
    Base class for storage-backend-specific subclasses.
    """
    pass

class R3dMetricStore(MetricStore):
    """
    Base class for R3D-backed metric stores.
    """
    def _default_rra_fn(db):
        """
        Configure a default set of RRAs for a new database.  Subclasses
        may (and probably should) override this layout.
        """
        # This isn't an ideal layout, but it's probably best to default to
        # collecting too much.  The subclasses should define something which
        # makes more sense for the metrics being collected.

        # 60 rows of 1 sample = 10 minutes of 10s samples
        db.archives.add(Average.objects.create(xff=0.5,
                                               database=db,
                                               cdp_per_row=1,
                                               rows=60))
        db.archives.add(Min.objects.create(xff=0.5,
                                           database=db,
                                           cdp_per_row=1,
                                           rows=60))
        db.archives.add(Max.objects.create(xff=0.5,
                                           database=db,
                                           cdp_per_row=1,
                                           rows=60))
        # 60 rows of 6 consolidated samples = 60 minutes of 1 minute samples
        db.archives.add(Average.objects.create(xff=0.5,
                                               database=db,
                                               cdp_per_row=6,
                                               rows=60))
        db.archives.add(Min.objects.create(xff=0.5,
                                           database=db,
                                           cdp_per_row=6,
                                           rows=60))
        db.archives.add(Max.objects.create(xff=0.5,
                                           database=db,
                                           cdp_per_row=6,
                                           rows=60))
        # 168 rows of 360 consolidated samples = 7 days of 1hr samples
        db.archives.add(Average.objects.create(xff=0.5,
                                               database=db,
                                               cdp_per_row=360,
                                               rows=168))
        db.archives.add(Min.objects.create(xff=0.5,
                                           database=db,
                                           cdp_per_row=360,
                                           rows=168))
        db.archives.add(Max.objects.create(xff=0.5,
                                           database=db,
                                           cdp_per_row=360,
                                           rows=168))
        # 365 rows of 8640 consolidated samples = 1 year of 1 day samples
        db.archives.add(Average.objects.create(xff=0.5,
                                               database=db,
                                               cdp_per_row=8640,
                                               rows=365))
        db.archives.add(Min.objects.create(xff=0.5,
                                           database=db,
                                           cdp_per_row=8640,
                                           rows=365))
        db.archives.add(Max.objects.create(xff=0.5,
                                           database=db,
                                           cdp_per_row=8640,
                                           rows=365))

    def _create_r3d(self, measured_object, rra_create_fn=_default_rra_fn,
                    **kwargs):
        """
        Creates a new R3D Database and associates it with the given
        measured object via ContentType.
        """
        ct = ContentType.objects.get_for_model(measured_object.downcast())
        self.r3d = Database.objects.create(name=measured_object.__str__(),
                                           object_id=measured_object.id,
                                           content_type=ct,
                                           step=settings.AUDIT_PERIOD,
                                           **kwargs)
        rra_create_fn(self.r3d)

        metrics_log.info("Created R3D: %s (%s)" % (ct, measured_object))

    def __init__(self, measured_object, **kwargs):
        """
        Given an object to wrap with MetricStore capabilities, either
        retrieves the existing associated R3D Database or creates one.
        """
        try:
            ct = ContentType.objects.get_for_model(measured_object.downcast())
            self.r3d = Database.objects.get(object_id=measured_object.id,
                                            content_type=ct)
        except Database.DoesNotExist:
            self._create_r3d(measured_object, **kwargs)

    def _sanitize_metric_name(self, prefix, dirty, suffix=None):
        """
        Utility method for ensuring that metric names contain only
        alnum characters.
        """
        clean = "%s%s" % (prefix, re.sub("[^\w]", "_", dirty))
        if suffix:
            clean += suffix
        return clean

    def _update_time(self):
        """
        Utility method for returning the current time as an int.  Used
        when constructing R3D updates prior to passing them into R3D.
        """
        import time
        return int(time.time())

    def list(self):
        """Returns a list of metric names for this wrapper's database."""
        return [ds.name for ds in self.r3d.datasources.all()]

    def fetch(self, cfname, **kwargs):
        """
        fetch(CFNAME [, fetch_metrics=['name'],
                      start_time=int, end_time=int])

        Given a consolidation function (Average, Min, Max, Last),
        an optional list of desired metrics, an optional start time,
        and an optinal end time, returns a dict containing rows of
        datapoints retrieved from the appropriate RRA.
        """
        return self.r3d.fetch(cfname, **kwargs)

    def fetch_last(self, fetch_metrics=None):
        """
        fetch_last([fetch_metrics=['name'])

        Returns a list containing a single row of datapoints
        taken from the last reading of each datasource.  Takes
        an optional list of metrics to filter output.
        """
        return self.r3d.fetch_last(fetch_metrics)

class HostMetricStore(R3dMetricStore):
    """
    Wrapper class for ManagedHost metrics.
    """
    def __init__(self, *args, **kwargs):
        def host_rra_fn(db):
            # I don't think we need the high resolution (10s/1m) samples for
            # CPU/Memory metrics.

            # 20 rows of 30 consolidated samples = 60 minutes of 5 min samples
            db.archives.add(Average.objects.create(xff=0.5,
                                                   database=db,
                                                   cdp_per_row=30,
                                                   rows=20))
            db.archives.add(Min.objects.create(xff=0.5,
                                               database=db,
                                               cdp_per_row=30,
                                               rows=20))
            db.archives.add(Max.objects.create(xff=0.5,
                                               database=db,
                                               cdp_per_row=30,
                                               rows=20))
            # 168 rows of 360 consolidated samples = 7 days of 1hr samples
            db.archives.add(Average.objects.create(xff=0.5,
                                                   database=db,
                                                   cdp_per_row=360,
                                                   rows=168))
            db.archives.add(Min.objects.create(xff=0.5,
                                               database=db,
                                               cdp_per_row=360,
                                               rows=168))
            db.archives.add(Max.objects.create(xff=0.5,
                                               database=db,
                                               cdp_per_row=360,
                                               rows=168))
            # 365 rows of 8640 consolidated samples = 1 year of 1 day samples
            db.archives.add(Average.objects.create(xff=0.5,
                                                   database=db,
                                                   cdp_per_row=8640,
                                                   rows=365))
            db.archives.add(Min.objects.create(xff=0.5,
                                               database=db,
                                               cdp_per_row=8640,
                                               rows=365))
            db.archives.add(Max.objects.create(xff=0.5,
                                               database=db,
                                               cdp_per_row=8640,
                                               rows=365))

        super(HostMetricStore, self).__init__(*args,
                                              rra_create_fn=host_rra_fn,
                                              **kwargs)
    def update(self, metrics):
        """
        Accepts a dict of host/lnet metrics as generated by hydra-agent
        and stores it in the associated R3D.
        """
        update = {}

        try:
            for key in metrics['meminfo']:
                ds_name = self._sanitize_metric_name("mem_", key)
                update[ds_name] = {'value': metrics['meminfo'][key],
                                   'type': 'Gauge'}
            for key in metrics['cpustats']:
                ds_name = self._sanitize_metric_name("cpu_", key)
                update[ds_name] = {'value': metrics['cpustats'][key],
                                   'type': 'Gauge'}
        except KeyError:
            pass

        try:
            for key in metrics['lnet']:
                ds_name = self._sanitize_metric_name("lnet_", key)
                ds_type = "Counter" if "_count" in ds_name else "Gauge"
                ds_type = "Counter" if ds_name == "errors" else ds_type
                update[ds_name] = {'value': metrics['lnet'][key],
                                   'type': ds_type}
        except KeyError:
            pass

        def missing_ds_fn(db, key, value):
            db.datasources.add(Gauge.objects.create(name=key,
                                                    heartbeat=db.step * 2,
                                                    database=db))
            metrics_log.info("Added new DS to DB (%s -> %s)" % (key, db.name))

        self.r3d.update({self._update_time(): update}, missing_ds_fn)

class TargetMetricStore(R3dMetricStore):
    """
    Wrapper class for Lustre Target metrics.
    """
    def update(self, metrics):
        """
        Accepts a dict of Lustre target metrics as generated by hydra-agent
        and stores it in the associated R3D.
        """
        update = {}

        stats = {}
        brw_stats = {}
        for key in metrics:
            if key == "stats":
                stats = metrics[key]
            elif key == "brw_stats":
                brw_stats = metrics[key]
            else:
                ds_name = self._sanitize_metric_name("", key)
                update[ds_name] = {'value': metrics[key], 'type': 'Gauge'}

        for key in stats:
            ds_name = self._sanitize_metric_name("stats_", key)
            if "sum" in stats[key]:
                if stats[key]['units'] == "reqs":
                    update[ds_name] = {'value': stats[key]['count'],
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
        #            ds_name = self._sanitize_metric_name("brw_", "%s_%s_" % (key, bucket), direction)
        #            update[ds_name] = brw_stats[key]['buckets'][bucket][direction]['count']

        def missing_ds_fn(db, key, payload):
            ct = ContentType.objects.get(model=payload['type'])
            ds_klass = ct.model_class()

            db.datasources.add(ds_klass.objects.create(name=key,
                                                       heartbeat=db.step * 2,
                                                       database=db))
            metrics_log.info("Added new DS to DB (%s -> %s)" % (key, db.name))

        self.r3d.update({self._update_time(): update}, missing_ds_fn)

class FilesystemMetricStore(R3dMetricStore):
    """
    Wrapper class for Filesystem-level aggregate metrics.  Read-only.
    """
    def __init__(self, managed_object, **kwargs):
        # Override the parent __init__(), as we don't need an R3D for
        # a Filesystem.
        self.filesystem = managed_object

    def update(self, *args, **kwargs):
        """Don't use this -- will raise a NotImplementedError!"""
        raise NotImplementedError, "Filesystem-level update() not supported!"

    def list(self, target_class):
        """
        list(target_class)

        Given a target class (ObjectStoreTarget, Metadatatarget, etc.),
        returns a list of metric names found in all target metrics.
        """
        metric_names = []

        for target in target_class.objects.filter(filesystem=self.filesystem):
            metric_names.extend(target.metrics.list())

        # stupid de-dupe hack
        set = {}
        map(set.__setitem__, metric_names, [])
        return set.keys()

    def fetch(self, cfname, target_class, **kwargs):
        """
        fetch(CFNAME, target_class [, fetch_metrics=['name'],
                      start_time=int, end_time=int])

        Given a consolidation function (Average, Min, Max, Last),
        a target class (ObjectStoreTarget, MetadataTarget, ManagmentTarget)
        an optional list of desired metrics, an optional start time,
        and an optinal end time, returns a dict containing rows of
        aggregate datapoints retrieved from the appropriate RRAs.
        """
        results = {}

        for target in target_class.objects.filter(filesystem=self.filesystem):
            tm = target.metrics.fetch(cfname, **kwargs)
            for row in tm.keys():
                if not results.has_key(row):
                    results[row] = {}

                for metric in tm[row].keys():
                    try:
                        if math.isnan(tm[row][metric]):
                            results[row][metric] += 0
                        else:
                            results[row][metric] += tm[row][metric]
                    except KeyError:
                        results[row][metric] = tm[row][metric]

        return results

    def fetch_last(self, target_class, fetch_metrics=None):
        """
        fetch_last(target_class [, fetch_metrics=['metric']])

        Given a target class (ObjectStoreTarget, Metadatatarget, etc),
        and an optional list of desired metrics, returns a list
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
                    if math.isnan(tm[1][metric]):
                        results[1][metric] += 0
                    else:
                        results[1][metric] += tm[1][metric]
                except KeyError:
                    results[1][metric] = tm[1][metric]

        return results

class VendorMetricStore(R3dMetricStore):
    """
    Wrapper class for vendor-specific metrics.
    """
    pass

def get_instance_metrics(measured_object):
    """
    Convenience method which allows retrieval of the associated
    MetricStore wrapper for a given object.

    Returns the wrapper for known object types, or None.
    """

    if hasattr(measured_object.downcast(), "host_ptr"):
        return HostMetricStore(measured_object)
    elif hasattr(measured_object.downcast(), "target_ptr"):
        return TargetMetricStore(measured_object)
    elif hasattr(measured_object.downcast(), "filesystem_ptr"):
        return FilesystemMetricStore(measured_object)
    else:
        return None
