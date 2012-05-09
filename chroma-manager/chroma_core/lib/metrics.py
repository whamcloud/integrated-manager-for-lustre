#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import math
from django.contrib.contenttypes.models import ContentType
from chroma_core.models.storage_plugin import StorageResourceStatistic
from r3d.models import Average, Database
from r3d.exceptions import BadUpdateTime
from chroma_core.lib.storage_plugin.api import statistics

import settings
metrics_log = settings.setup_log('metrics')


class MetricStore(object):
    """
    Base class for storage-backend-specific subclasses.
    """
    pass


def _autocreate_ds(db, key, payload):
    # FIXME should include the app label in this query to avoid risk of
    # name overlap with other apps
    ct = ContentType.objects.get(model=payload['type'])
    ds_klass = ct.model_class()

    new_ds = ds_klass.objects.create(name=key,
                                     heartbeat=db.step * 2,
                                     database=db)
    db.datasources.add(new_ds)
    metrics_log.info("Added new %s to DB (%s -> %s)" % (payload['type'],
                                                        key, db.name))
    return new_ds


class R3dMetricStore(MetricStore):
    """
    Base class for R3D-backed metric stores.
    """
    def _create_r3d(self,
            measured_object,
            sample_period,
            **kwargs):
        """
        Creates a new R3D Database and associates it with the given
        measured object via ContentType.
        """
        def _default_rra_fn(db):
            """
            Configure a default set of RRAs for a new database.  Subclasses
            may (and probably should) override this layout.
            """
            # 8640 rows of 1 sample = 1 day of 10s samples
            db.archives.add(Average.objects.create(xff=0.5,
                database=db,
                cdp_per_row=1,
                rows=8640))
            # 10080 rows of 6 consolidated samples = 1 week of 1 minute samples
            db.archives.add(Average.objects.create(xff=0.5,
                database=db,
                cdp_per_row=6,
                rows=10080))
            # 8760 rows of 30 consolidated samples = 1 month of 5 minute samples
            db.archives.add(Average.objects.create(xff=0.5,
                database=db,
                cdp_per_row=30,
                rows=8760))
            # 262800 rows of 60 consolidated samples = 5 years of 10 minute samples
            db.archives.add(Average.objects.create(xff=0.5,
                database=db,
                cdp_per_row=60,
                rows=262800))

        def _minimal_archives(db):
            """
            Workaround performance issues, create the least possible archives
            """
            # 60 rows of 1 sample = 10 minutes of 10s samples
            db.archives.add(Average.objects.create(xff=0.5,
                database=db,
                cdp_per_row=1,
                rows=60))

        # FIXME: because of stats storage performance issues,
        # only store very short period of data for (numerous)
        # storage resource statistics.
        if isinstance(measured_object, StorageResourceStatistic):
            metrics_log.debug('minimal archive for %s' % measured_object)
            rra_create_fn = _minimal_archives
        else:
            metrics_log.debug('full archive for %s' % measured_object)
            rra_create_fn = _default_rra_fn

        # We want our start time to be prior to the first insert, but
        # not so far back that we waste lots of time with filling in
        # null data.
        # FIXME HYD-366: this should be set at first insert.
        import time
        start_time = int(time.time()) - 1

        ct = ContentType.objects.get_for_model(measured_object)
        db_name = "%s-%d" % (ct, measured_object.id)
        r3d, created = Database.objects.get_or_create(
                                                name=db_name,
                                                start=start_time,
                                                object_id=measured_object.id,
                                                content_type=ct,
                                                step=sample_period,
                                                **kwargs)
        rra_create_fn(r3d)

        if created:
            metrics_log.info("Created R3D: %s (%s)" % (ct, measured_object))

        return r3d

    def clear(self):
        r3d = self.get_r3d()
        if r3d:
            r3d.delete()

    def get_r3d(self, create = False):
        try:
            ct = ContentType.objects.get_for_model(self.measured_object)
            mo_id = self.measured_object.id
            return Database.objects.get(object_id=mo_id,
                content_type=ct)
        except Database.DoesNotExist:
            if create:
                return self._create_r3d(self.measured_object, self.sample_period)
            else:
                return None

    def __init__(self, measured_object, sample_period = None):
        """
        Given an object to wrap with MetricStore capabilities, either
        retrieves the existing associated R3D Database or creates one.
        """
        self.measured_object = measured_object
        if hasattr(self.measured_object, 'content_type'):
            self.measured_object = self.measured_object.downcast()
        self.sample_period = sample_period

    def _update_time(self):
        """
        Utility method for returning the current time as an int.  Used
        when constructing R3D updates prior to passing them into R3D.
        """
        import time
        return int(time.time())

    def update_r3d(self, update):
        try:
            r3d = self.get_r3d(create = True)
            r3d.update(update, _autocreate_ds)
        except BadUpdateTime:
            metrics_log.warn("Discarding %d update for %s" % (update.keys()[0],
                                                              self))

    def list(self):
        """Returns a dict of name:type pairs for this wrapper's database."""
        r3d = self.get_r3d()
        if r3d:
            return dict([[ds.name, ds.__class__.__name__]
                     for ds in r3d.datasources.all()])
        else:
            return {}

    def fetch(self, cfname, **kwargs):
        """
        fetch(CFNAME [, fetch_metrics=['name'],
                      start_time=int, end_time=int])

        Given a consolidation function (Average, Min, Max, Last),
        an optional list of desired metrics, an optional start time,
        and an optinal end time, returns a dict containing rows of
        datapoints retrieved from the appropriate RRA.
        """
        r3d = self.get_r3d()
        if r3d:
            return r3d.fetch(cfname, **kwargs)
        else:
            return {}

    def fetch_last(self, fetch_metrics=None):
        """
        fetch_last([fetch_metrics=['name'])

        Returns a list containing a single row of datapoints
        taken from the last reading of each datasource.  Takes
        an optional list of metrics to filter output.
        """
        r3d = self.get_r3d()
        if r3d:
            return r3d.fetch_last(fetch_metrics)
        else:
            return [0, {}]


class VendorMetricStore(R3dMetricStore):
    def __init__(self, *args, **kwargs):
        super(VendorMetricStore, self).__init__(*args, **kwargs)

    def update(self, stat_name, stat_properties, stat_data):
        """stat_data is an iterable in time order of dicts, where each
           dict has a member 'timestamp' which is a timestamp int, and
           'value' whose type depends on the statistic"""
        r3d_format = {}

        for datapoint in stat_data:
            ts = datapoint['timestamp']
            val = datapoint['value']
            if isinstance(stat_properties, statistics.Gauge):
                r3d_format[ts] = {stat_name: {'value': val, 'type': 'Gauge'}}
            elif isinstance(stat_properties, statistics.Counter):
                r3d_format[ts] = {stat_name: {'value': val, 'type': 'Counter'}}
            elif isinstance(stat_properties, statistics.BytesHistogram):
                bins_dict = {}
                for i in range(0, len(val)):
                    bin_stat_name = "%s_%s" % (stat_name, i)
                    bins_dict[bin_stat_name] = {'value': val[i], 'type': 'Gauge'}
                r3d_format[ts] = bins_dict

        # Skipping sanitize
        self.get_r3d(create = True).update(r3d_format, _autocreate_ds)


class HostMetricStore(R3dMetricStore):
    """
    Wrapper class for ManagedHost metrics.
    """
    def update(self, metrics, update_time=None):
        """
        Accepts a dict of host/lnet metrics as generated by chroma-agent
        and stores it in the associated R3D.
        """
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

        count = len(update.keys())

        self.update_r3d({update_time: update})

        return count


class TargetMetricStore(R3dMetricStore):
    """
    Wrapper class for Lustre Target metrics.
    """
    def update(self, metrics, update_time=None):
        """
        Accepts a dict of Lustre target metrics as generated by chroma-agent
        and stores it in the associated R3D.
        """
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
                ds_name = key
                update[ds_name] = {'value': metrics[key], 'type': 'Gauge'}

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

        count = len(update.keys())

        self.update_r3d({update_time: update})

        return count


class FilesystemMetricStore(R3dMetricStore):
    """
    Wrapper class for Filesystem-level aggregate metrics.  Read-only.
    """
    def __init__(self, managed_object, *args, **kwargs):
        # Override the parent __init__(), as we don't need an R3D for
        # a Filesystem.
        self.filesystem = managed_object

    def update(self, *args, **kwargs):
        """Don't use this -- will raise a NotImplementedError!"""
        raise NotImplementedError("Filesystem-level update() not supported!")

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
                    if math.isnan(tm[1][metric]):
                        results[1][metric] += 0
                    else:
                        results[1][metric] += tm[1][metric]
                except KeyError:
                    results[1][metric] = tm[1][metric]

        return tuple(results)


def get_instance_metrics(measured_object):
    """
    Convenience method which allows retrieval of the associated
    MetricStore wrapper for a given object.

    Returns the wrapper for known object types, or raises NotImplementedError.
    """

    from chroma_core.models import ManagedHost, ManagedTarget, ManagedFilesystem
    if isinstance(measured_object, ManagedHost):
        return HostMetricStore(measured_object, settings.AUDIT_PERIOD)
    elif isinstance(measured_object, ManagedTarget):
        return TargetMetricStore(measured_object, settings.AUDIT_PERIOD)
    elif isinstance(measured_object, ManagedFilesystem):
        return FilesystemMetricStore(measured_object, settings.AUDIT_PERIOD)
    else:
        raise NotImplementedError
