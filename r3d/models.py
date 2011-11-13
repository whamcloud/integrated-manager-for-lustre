## Copyright 2011 Whamcloud, Inc.
## Authors: Michael MacDonald <mjmac@whamcloud.com>

from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
import time, math
from r3d.exceptions import *
from r3d import lib
from r3d.lib import DNAN, DINF, debug_print

class SciFloatField(models.FloatField):
    """
    Basic FloatField class, but aware of NaN/Inf.  When the value retrieved from 
    the DB is NULL (None), converts it to float("NaN").  Conversely, when the
    value to be saved in the DB is float("NaN"), converts it to None (NULL).

    For Inf, we need to rely on a bit of hackery.  The largest signed double
    we can store in MySQL is 1.7976931348623157e308, so we'll use that to
    represent Inf in the DB.
    """
    __metaclass__ = models.SubfieldBase

    def get_prep_value(self, value):
        if isinstance(value, float) and math.isnan(value):
            return None
        elif isinstance(value, float) and math.isinf(value):
            hack_inf = '1.7976931348623157e308'
            return hack_inf if value > 0 else "-%s" % hack_inf
        else:
            return value

    def to_python(self, value):
        if value is None:
            return float("NaN")
        elif (isinstance(value, float) and
              abs(value / 1.7976931348623157e308) == 1):
            return float("Inf") if value > 0 else -float("Inf")
        else:
            return value

class Database(models.Model):
    """
    An R3D Database is the container for all other R3D entities.
    Attributes:
      name      description                 type    required?   default
      name      db identifier               string  True        n/a
      start     earliest entry time         int     False       now - 86400
      step      input interval in seconds   int     False       300

    # Create an r3d DB with default attributes
    >>> rrd = Database.objects.create(name="testdb")

    # Note that the default start time should be around a day ago, the default
    # step value is 300, and the last_update value starts off being equal
    # to the start time.
    >>> import time
    >>> yesterday = time.time() - 86400
    >>> rrd.start > yesterday - 60
    True
    >>> rrd.start < yesterday + 60
    True
    >>> rrd.step
    300
    >>> rrd.start == rrd.last_update
    True
    """
    @classmethod
    def default_start(cls):
        return int(time.time() - 86400)

    name        = models.CharField(max_length=255, unique=True)
    start       = models.BigIntegerField(default=lambda: Database.default_start())
    step        = models.BigIntegerField(default=300)
    last_update = models.BigIntegerField(blank=True)

    # Leverage the ContentTypes framework to allow R3D databases to be
    # optionally associated with other apps' models.
    content_type    = models.ForeignKey(ContentType, null=True)
    object_id       = models.PositiveIntegerField(null=True)
    content_object  = generic.GenericForeignKey('content_type', 'object_id')

    class Meta:
        unique_together = ('content_type', 'object_id')

    def _parse_time(self, in_time):
        if hasattr(in_time, "now"):
            return int(in_time.strftime("%s"))
        elif hasattr(in_time, "numerator"):
            # skip pointless conversions if it's already an int
            return in_time
        else:
            return int(float(in_time))

    def __init__(self, *args, **kwargs):
        if kwargs.has_key("start"):
            kwargs['start'] = self._parse_time(kwargs['start'])

        super(Database, self).__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        if not self.last_update:
            self.last_update = self.start
        super(Database, self).save(*args, **kwargs)

    # FIXME: The fancy-pants delete() doesn't seem to handle entities
    # with more than one FK reference.  Or something.  Go back and figure
    # it out later.
    def delete(self, *args, **kwargs):
        for ds in self.datasources.all():
            ds.delete(*args, **kwargs)
        for rra in self.archives.all():
            rra.delete(*args, **kwargs)
        super(Database, self).delete(*args, **kwargs)

    def single_update(self, update_time, new_values):
        interval = float(update_time) - float(self.last_update)

        debug_print("vvv--------------------------------------------------vvv")

        if len(new_values) != len(self.ds_cache):
            raise BadUpdateString, "Update string DS count doesn't match database DS count"

        if interval < 1:
            raise BadUpdateTime, "Illegal update time %d (minimum one second step from %d)" % (update_time, self.last_update)

        (elapsed_steps,
         pre_int,
         post_int,
         pdp_count) = lib.calculate_elapsed_steps(self.last_update,
                                                  self.step,
                                                  update_time,
                                                  interval)

        # Update each DS's internal counters using the new reading.
        for idx in range(0, len(self.ds_cache)):
            self.ds_cache[idx].add_new_reading(new_values[idx],
                                               update_time,
                                               interval)

        if elapsed_steps == 0:
            # If we haven't crossed a step threshold, then we don't
            # want to consolidate any datapoints.  Just update the DS
            # scratch counters.
            debug_print("simple update")
            lib.simple_update(self.ds_cache,
                              update_time,
                              interval)
        else:
            # If we have crossed one (or more) step thresholds, then
            # we need to run through and consolidate all DS PDPs.
            debug_print("consolidation needed")
            lib.consolidate_all_pdps(self,
                                     interval,
                                     elapsed_steps,
                                     pre_int,
                                     post_int,
                                     pdp_count)

        self.last_update = update_time
        self.save(force_update=True)

        debug_print("^^^--------------------------------------------------^^^")

    def load_cached_associations(self):
        # Try to preload stuff as much as possible.
        self.pdp_cache = list(PdpPrep.objects.select_related().filter(datasource__database__id=self.id).order_by('datasource'))
        # This is ass-backwards, but that's django for you.
        self.ds_cache = [pdp.datasource for pdp in self.pdp_cache]

        self.rra_cache = list(self.archives.order_by('id'))
        self.pcdp_cache = list(CdpPrep.objects.select_related().filter(archive__database__id=self.id).order_by('datasource', 'archive'))

    def parse_update_dict(self, update, missing_ds_block=None):
        new_values = []

        # First, get new readings for all of the DSes we know about.
        for ds in self.ds_cache:
            try:
                ds_update = update.pop(ds.name)
                # handle either style of update dict
                try:
                    new_values.append(ds_update['value'])
                except TypeError:
                    new_values.append(ds_update)
            except KeyError:
                # no news is still news
                new_values.append(DNAN)

        # Now, if there's anything left over, we'll let the caller create
        # DS/RRA entries, if it bothered to try.
        if len(update.keys()) > 0 and missing_ds_block:
            for key in update.keys():
                missing_ds_block(self, key, update[key])
                ds_update = update.pop(key)
                try:
                    new_values.append(ds_update['value'])
                except TypeError:
                    new_values.append(ds_update)

            # Reload caches
            self.load_cached_associations()
        elif len(update.keys()) > 0:
            raise ValueError, "Unknown metrics: %s" % update.keys()

        return new_values

    def update(self, updates, missing_ds_block=None):
        """
        Receives either:
        an RRD-style update string (update_time:ds_val_0..ds_val_N)
        or a dict containing one or more update dicts {time: {ds_name: ds_val, ...}}
        and updates the corresponding DS PDPs/CDPs.

        No return value.
        """
        self.load_cached_associations()

        if hasattr(updates, "partition"):
            update_time, new_values = lib.parse_update_string(updates)
            self.single_update(update_time, new_values)
        else:
            for update in sorted(updates.keys()):
                new_values = self.parse_update_dict(updates[update],
                                                    missing_ds_block)
                self.single_update(self._parse_time(update), new_values)

    def fetch(self, archive_type, start_time=None,
                                  end_time=None,
                                  step=1,
                                  fetch_metrics=None):
        """
        Fetches the set of CDPs for the given archive type between the
        interval specified by start_time and end_time.

        Returns a dict of CDP rows (time: {ds_name: cdp_val, ...}).
        """
        if not start_time:
            start_time = int(time.time() - 3600)
        if not end_time:
            end_time = int(time.time())

        return lib.fetch_best_rra_rows(self,
                                       archive_type,
                                       self._parse_time(start_time),
                                       self._parse_time(end_time),
                                       step,
                                       fetch_metrics)

    def fetch_last(self, fetch_metrics=None):
        """
        fetch_last([fetch_metrics=["name"]])

        Fetches the last reading for each DS.  Takes an optional
        list of metric names as a filter for the query.
        """
        results = {}

        if fetch_metrics is None:
            for ds in self.datasources.all():
                results[ds.name] = ds.prep.last_reading
        else:
            for ds in self.datasources.filter(name__in=fetch_metrics):
                results[ds.name] = ds.prep.last_reading

        return (self.last_update, results)

    def dump(self):
        """
        dump()

        Dump the database contents to JSON.
        """
        from django.core.serializers import serialize
        import json

        output = []
        output.append(serialize("json", Database.objects.filter(id=self.id)))
        output.append(serialize("json", self.datasources.all()))
        output.append(serialize("json", self.archives.all()))
        for rra in self.archives.all():
            output.append(serialize("json", Archive.objects.filter(id=rra.id)))
            for ds in self.datasources.all():
                output.append(serialize("json", rra.preps.filter(datasource=ds.id)))
            ds_cdps =  {}
            for ds in self.datasources.all():
                ds_cdps[ds] = rra.ds_cdps(ds)

            for idx in range(0, rra.rows):
                row_vals = []
                try:
                    for ds in self.datasources.all():
                        row_vals.append(ds_cdps[ds][idx].value)
                except IndexError:
                    continue
                output.append(json.dumps([idx, row_vals]))

        return "\n".join([json.dumps(o, indent=2) for o in 
                          [json.loads(j) for j in output]])

    def purge_cdps(self):
        debug_print("Housekeeping: Deleting old CDPs")

        old_cdps = []
        for rra in self.archives.all():
            for ds in self.datasources.all():
                old_cdps.extend(rra.find_obsolete_cdps(ds))

        if len(old_cdps) > 0:
            # We can avoid a useless select if we just nuke the
            # old CDPs directly.
            from django.db import connection, transaction
            cursor = connection.cursor()
            cursor.execute("DELETE FROM r3d_cdp WHERE id IN (%s)" %
                           ",".join(old_cdps))
            transaction.commit_unless_managed()

        debug_print("deleted %d old CDPs" % len(old_cdps))

# http://djangosnippets.org/snippets/2408/
# Grumble.
from abc import abstractmethod
class PoorMansStiModel(models.Model):
    classes = dict()
    mod = models.CharField(max_length=50)
    cls = models.CharField(max_length=30)

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        super(PoorMansStiModel, self).__init__(*args, **kwargs)
        if self.cls:
            if not PoorMansStiModel.classes.has_key(self.cls):
                x = getattr(__import__(self.mod, globals(), locals(),
                                       [self.cls]), self.cls)
                self.__class__ = x
            else:
                self.__class__ = PoorMansStiModel.classes[(self.mod, self.cls)]

    def save(self, *args, **kwargs):
        if not self.cls:
            self.cls = self.__class__.__name__
        if not self.mod:
            self.mod = self.__class__.__module__
        super(PoorMansStiModel, self).save(*args, **kwargs)

class Datasource(PoorMansStiModel):
    """
    A Datasource identifies a source of Primary Data Points.
    """
    database        = models.ForeignKey(Database, related_name="datasources")
    name            = models.CharField(max_length=255)
    heartbeat       = models.BigIntegerField()
    min_reading     = SciFloatField(null=True, blank=True)
    max_reading     = SciFloatField(null=True, blank=True)

    class Meta:
        unique_together = ("database", "name")

    def save(self, *args, **kwargs):
        new_ds = False
        if self.id is None:
            new_ds = True

        super(Datasource, self).save(*args, **kwargs)

        if new_ds:
            # If this is a new DS, try to precreate the Prep/CDP entities.
            # If there are no Archives defined yet, this won't do anything,
            # and the entities will be precreated when the Archives are
            # defined.  This path should only be taken when a DS is added
            # after a Database has already been set up.
            prep = PdpPrep(datasource=self)
            prep.save(new_prep=True, force_insert=True)
            for rra in self.database.archives.all():
                debug_print("Associating new DS with rra: %s" % rra.__dict__)
                rra.create_ds_prep(self)
                rra.create_filler_cdps(self)

    # This seems to be necessary to avoid integrity errors on delete.  Grumble.
    def delete(self, *args, **kwargs):
        self.prep.delete(*args, **kwargs)
        for prep in self.preps.all():
            prep.delete(*args, **kwargs)
        for cdp in self.cdps.all():
            cdp.delete(*args, **kwargs)
        super(Datasource, self).delete(*args, **kwargs)

    def transform_reading(self, value, update_time, interval):
        return value

    def add_new_reading(self, new_reading, update_time, interval):
        # stash this for debugging
        saved_last = self.prep.last_reading

        if self.heartbeat < interval:
            self.prep.last_reading = DNAN

        if math.isnan(new_reading) or self.heartbeat < interval:
            self.prep.new_val = DNAN
        else:
            self.prep.new_val = self.transform_reading(new_reading,
                                                       update_time,
                                                       interval)

            # Make sure that we're inside the bounds defined by the DS.
            try:
                rate = self.prep.new_val / interval
            except ZeroDivisionError:
                rate = DNAN

            if (not math.isnan(rate) and
                ((not math.isnan(self.max_reading) and
                  rate > self.max_reading)) or
                ((not math.isnan(self.min_reading) and
                  rate < self.min_reading))):
                self.prep.new_val = DNAN

        # save this for the next run
        self.prep.last_reading = new_reading

        debug_print("%s @ %d: (%10.2f) %10.2f -> %10.2f" % (self.name, update_time, saved_last, new_reading, self.prep.new_val))

class Absolute(Datasource):
    """
    Absolute counters get reset upon reading. This is used for fast counters
    which tend to overflow. So instead of reading them normally you reset
    them after every read to make sure you have a maximum time available
    before the next overflow. Another usage is for things you count like
    number of messages since the last update.

    >>> rrd = Database.objects.create(name="abs_test")
    >>> rrd.datasources.add(Absolute.objects.create(name="absolute_ds",
    ...                                             heartbeat=300,
    ...                                             database=rrd))
    >>> ds = rrd.datasources.all()[0]
    >>> ds.name
    u'absolute_ds'
    """
    class Meta:
        proxy = True

class Counter(Datasource):
    """
    Counter is for continuous incrementing counters like the ifInOctets
    counter in a router. The COUNTER data source assumes that the counter
    never decreases, except when a counter overflows. The update function
    takes the overflow into account. The counter is stored as a per-second
    rate. When the counter overflows, a check is made for if the overflow
    happened at the 32bit or 64bit border and acts accordingly by adding
    an appropriate value to the result.

    >>> rrd = Database.objects.create(name="ctr_test")
    >>> rrd.datasources.add(Counter.objects.create(name="counter_ds",
    ...                                            heartbeat=300,
    ...                                            database=rrd))
    >>> ds = rrd.datasources.all()[0]
    >>> ds.name
    u'counter_ds'
    """
    class Meta:
        proxy = True

    def transform_reading(self, value, update_time, interval):
        if math.isnan(self.prep.last_reading) or math.isnan(value):
             return DNAN

        value -= self.prep.last_reading

        if value < 0.0:
            value += 4294967296.0 # 2^32

        if value < 0.0:
            value += 18446744069414584320.0 # 2^64-2^32

        return value

class Derive(Datasource):
    """
    Derive will store the derivative of the line going from the last to the
    current value of the data source. This can be useful for gauges, for
    example, to measure the rate of people entering or leaving a room.
    Internally, derive works exactly like COUNTER but without overflow
    checks. So if your counter does not reset at 32 or 64 bit you might
    want to use DERIVE and combine it with a MIN value of 0.

    >>> rrd = Database.objects.create(name="derive_test")
    >>> rrd.datasources.add(Derive.objects.create(name="derive_ds",
    ...                                           heartbeat=300,
    ...                                           database=rrd))
    >>> ds = rrd.datasources.all()[0]
    >>> ds.name
    u'derive_ds'
    """
    class Meta:
        proxy = True

    def transform_reading(self, value, update_time, interval):
        if math.isnan(self.prep.last_reading):
            return DNAN
        else:
            return value - self.prep.last_reading

class Gauge(Datasource):
    """
    Stores the current reading (e.g. temperature, stock price, etc.)

    >>> rrd = Database.objects.create(name="gauge_test")
    >>> rrd.datasources.add(Gauge.objects.create(name="gauge_ds",
    ...                                          heartbeat=300,
    ...                                          database=rrd))
    >>> ds = rrd.datasources.all()[0]
    >>> ds.name
    u'gauge_ds'
    """
    class Meta:
        proxy = True

    def transform_reading(self, value, update_time, interval):
        return value * interval

class PdpPrep(models.Model):
    """
    Provides storage for primary data points prior to consolidation.
    """
    datasource      = models.OneToOneField(Datasource,
                                           primary_key=True,
                                           related_name="prep")
    last_reading    = SciFloatField(null=True)
    scratch         = SciFloatField(null=True, default=0.0)
    unknown_seconds = models.BigIntegerField(default=0)

    # ephemeral attributes
    new_val       = DNAN
    temp_val      = DNAN

    def save(self, new_prep=False, *args, **kwargs):
        if new_prep:
            # We need to initialize the unknown seconds counter based
            # on where we are relative to the last update and the next
            # step.
            self.unknown_seconds = (self.datasource.database.last_update %
                                    self.datasource.database.step)

        super(PdpPrep, self).save(*args, **kwargs)

class Archive(PoorMansStiModel):
    """
    An Archive represents a fixed set of rows, each containing
    time-based consolidated data points (CDPs) for associated Datasources.
    A given Archive has a specific resolution (number of primary data points
    per CDP).
    """
    # persistent record fields
    database        = models.ForeignKey(Database, related_name="archives")
    xff             = SciFloatField(default=0.5)
    cdp_per_row     = models.BigIntegerField()
    rows            = models.BigIntegerField()
    current_row     = models.BigIntegerField(default=0)

    # ephemeral attributes
    steps_since_update = 0
    nan_cdps           = 0

    def create_filler_cdps(self, ds):
        # When a DS has been added after the initial inserts, we need to
        # create "filler" CDPs to make the number of DB rows match the RRA's
        # current row count. This is ugly, but hopefully shouldn't happen
        # too often.
        for i in range(0, self.current_row):
            self.cdps.add(CDP.objects.create(archive=self, datasource=ds))

    def create_ds_prep(self, ds):
        # This will result in a constraint violation if it's a duplicate.
        self.preps.add(CdpPrep.objects.create(archive=self,
                                              datasource=ds))

    def seed_preps(self):
        for ds in self.database.datasources.all():
            self.create_ds_prep(ds)

    def save(self, *args, **kwargs):
        new_rra = False
        if self.id is None:
            new_rra = True

        super(Archive, self).save(*args, **kwargs)

        # On RRA create, we need to precreate the CdpPreps.
        if new_rra:
            self.seed_preps()

    # This seems to be necessary to avoid integrity errors on delete.  Grumble.
    def delete(self, *args, **kwargs):
        for prep in self.preps.all():
            prep.delete(*args, **kwargs)
        for cdp in self.cdps.all():
            cdp.delete(*args, **kwargs)
        super(Archive, self).delete(*args, **kwargs)

    def ds_cdps(self, ds):
        # Fetch the rows in reverse, newest to oldest, limited by the max
        # number of possible rows for this RRA.  Then reverse that list
        # for the consumer.
        cdps = list(self.cdps.filter(datasource=ds).order_by('-id')[:self.rows])
        cdps.reverse()
        return cdps

    def ds_prep(self, ds):
        return self.preps.filter(datasource=ds)[0]

    def store_ds_cdp(self, ds, cdp_prep):
        # First, create and insert the new CDP for this row.
        cdp = CDP(archive=self, datasource=ds, value=cdp_prep.primary)
        cdp.save(force_insert=True)
        debug_print("saved %10.2f -> datapoints[%d]" % (cdp.value,
                                                        self.current_row))

    def find_obsolete_cdps(self, ds):
       return ["%d" % cdp.id for cdp in
               self.cdps.filter(datasource=ds).order_by("-id")[self.rows:]]
 
    def purge_ds_cdps(self, ds):
        debug_print("Housekeeping: Deleting old CDPs")
        old = self.find_obsolete_cdps(self, ds)

        if len(old) > 0:
            # We can avoid a useless select if we just nuke the
            # old CDPs directly.
            from django.db import connection, transaction
            cursor = connection.cursor()
            cursor.execute("DELETE FROM r3d_cdp WHERE id IN (%s)" %
                           ",".join(old))
            transaction.commit_unless_managed()

        debug_print("deleted %d old CDPs" % len(old))

    def calculate_cdp_value(self, cdp_prep, ds, elapsed_steps):
        raise RuntimeError, "Method not implemented at this level"

    def initialize_cdp_value(self, cdp_prep, ds, start_pdp_offset):
        raise RuntimeError, "Method not implemented at this level"

    def carryover_cdp_value(self, cdp_prep, ds, elapsed_steps, start_pdp_offset):
        raise RuntimeError, "Method not implemented at this level"

class Average(Archive):
    """
    Stores the average of its data points.

    >>> rrd = Database.objects.create(name="avg_test")
    >>> rrd.archives.add(Average.objects.create(cdp_per_row=10,
    ...                                         rows=30,
    ...                                         database=rrd))
    >>> rra = rrd.archives.all()[0]
    >>> rra.rows
    30
    """
    class Meta:
        proxy = True

    def calculate_cdp_value(self, cdp_prep, ds, elapsed_steps):
        if math.isnan(cdp_prep.value):
            return ds.prep.temp_val * elapsed_steps

        return cdp_prep.value + ds.prep.temp_val * elapsed_steps

    def initialize_cdp_value(self, cdp_prep, ds, start_pdp_offset):
        cum_val = 0.0 if math.isnan(cdp_prep.value) else cdp_prep.value
        cur_val = 0.0 if math.isnan(ds.prep.temp_val) else ds.prep.temp_val
        primary = ((cum_val + cur_val * start_pdp_offset) /
                   (self.cdp_per_row - cdp_prep.unknown_pdps))
        debug_print("%10.9f = (%10.9f + %10.9f * %lu) / (%lu - %lu)" % (primary, cum_val, cur_val, start_pdp_offset, self.cdp_per_row, cdp_prep.unknown_pdps))
        return primary

    def carryover_cdp_value(self, cdp_prep, ds, elapsed_steps, start_pdp_offset):
        overlap_count = ((elapsed_steps - start_pdp_offset) % self.cdp_per_row)
        if overlap_count == 0 or math.isnan(ds.prep.temp_val):
            cdp_prep.value = 0
        else:
            cdp_prep.value = ds.prep.temp_val * overlap_count

class Last(Archive):
    """
    Stores the last (most current) data point.

    >>> rrd = Database.objects.create(name="lst_test")
    >>> rrd.archives.add(Last.objects.create(cdp_per_row=10,
    ...                                      rows=30,
    ...                                      database=rrd))
    >>> rra = rrd.archives.all()[0]
    >>> rra.rows
    30
    """
    class Meta:
        proxy = True

    def calculate_cdp_value(self, cdp_prep, ds, elapsed_steps):
        return ds.prep.temp_val

    def initialize_cdp_value(self, cdp_prep, ds, start_pdp_offset):
        return ds.prep.temp_val

    def carryover_cdp_value(self, cdp_prep, ds, elapsed_steps, start_pdp_offset):
        overlap_count = ((elapsed_steps - start_pdp_offset) % self.cdp_per_row)
        if overlap_count == 0 or math.isnan(ds.prep.temp_val):
            cdp_prep.value = DNAN
        else:
            cdp_prep.value = ds.prep.temp_val

class Max(Archive):
    """
    Stores the largest data point.

    >>> rrd = Database.objects.create(name="test_max")
    >>> rrd.archives.add(Max.objects.create(cdp_per_row=10,
    ...                                     rows=30,
    ...                                     database=rrd))
    >>> rra = rrd.archives.all()[0]
    >>> rra.rows
    30
    """
    class Meta:
        proxy = True

    def calculate_cdp_value(self, cdp_prep, ds, elapsed_steps):
        if math.isnan(cdp_prep.value):
            return ds.prep.temp_val

        return ds.prep.temp_val if (ds.prep.temp_val > cdp_prep.value) else cdp_prep.value

    def initialize_cdp_value(self, cdp_prep, ds, start_pdp_offset):
        cum_val = -DINF if math.isnan(cdp_prep.value) else cdp_prep.value
        cur_val = -DINF if math.isnan(ds.prep.temp_val) else ds.prep.temp_val

        if cur_val > cum_val:
            return cur_val
        else:
            return cum_val

    def carryover_cdp_value(self, cdp_prep, ds, elapsed_steps, start_pdp_offset):
        overlap_count = ((elapsed_steps - start_pdp_offset) % self.cdp_per_row)
        if overlap_count == 0 or math.isnan(ds.prep.temp_val):
            cdp_prep.value = -DINF
        else:
            cdp_prep.value = ds.prep.temp_val

class Min(Archive):
    """
    Stores the smallest data point.

    >>> rrd = Database.objects.create(name="test_min")
    >>> rrd.archives.add(Min.objects.create(cdp_per_row=10,
    ...                                     rows=30,
    ...                                     database=rrd))
    >>> rra = rrd.archives.all()[0]
    >>> rra.rows
    30
    """
    class Meta:
        proxy = True

    def calculate_cdp_value(self, cdp_prep, ds, elapsed_steps):
        if math.isnan(cdp_prep.value):
            return ds.prep.temp_val

        return ds.prep.temp_val if (ds.prep.temp_val < cdp_prep.value) else cdp_prep.value

    def initialize_cdp_value(self, cdp_prep, ds, start_pdp_offset):
        cum_val = DINF if math.isnan(cdp_prep.value) else cdp_prep.value
        cur_val = DINF if math.isnan(ds.prep.temp_val) else ds.prep.temp_val

        if cur_val < cum_val:
            return cur_val
        else:
            return cum_val

    def carryover_cdp_value(self, cdp_prep, ds, elapsed_steps, start_pdp_offset):
        overlap_count = ((elapsed_steps - start_pdp_offset) % self.cdp_per_row)
        if overlap_count == 0 or math.isnan(ds.prep.temp_val):
            cdp_prep.value = DINF
        else:
            cdp_prep.value = ds.prep.temp_val

class CDP(models.Model):
    """
    Stores a Datasource's data points after they've been run through
    the associated Archive's consolidation function.

    """
    archive         = models.ForeignKey(Archive,
                                        db_index=True,
                                        related_name="cdps")
    datasource      = models.ForeignKey(Datasource,
                                        db_index=True,
                                        related_name="cdps")
    value           = SciFloatField(null=True)

class CdpPrep(models.Model):
    """
    Provides temporary storage for data points during the consolidation
    process.
    """
    archive         = models.ForeignKey(Archive, related_name="preps")
    datasource      = models.ForeignKey(Datasource, related_name="preps")
    value           = SciFloatField(null=True)
    primary         = SciFloatField(null=True, default=0.0)
    secondary       = SciFloatField(null=True, default=0.0)
    unknown_pdps    = models.BigIntegerField(default=0)

    class Meta:
        unique_together = ("archive", "datasource")

    def save(self, *args, **kwargs):
        new_prep = False
        if self.id is None:
            new_prep = True

        if new_prep:
            # We need to initialize the unknown pdp counter based
            # on where we are in the archive's consolidation cycle.
            db_step = self.datasource.database.step
            db_update = self.datasource.database.last_update
            self.unknown_pdps = ((db_update - self.datasource.prep.unknown_seconds)
                                 % (db_step * self.archive.cdp_per_row)
                                 / db_step)

        super(CdpPrep, self).save(*args, **kwargs)

    def update(self, rra, ds, elapsed_steps, start_pdp_offset):
        debug_print("->update: ds.prep.temp_val %10.2f rra.steps_since_update %d elapsed_steps %d start_pdp_offset %d rra.cdp_per_row %d xff %10.2f" % (ds.prep.temp_val, rra.steps_since_update, elapsed_steps, start_pdp_offset, rra.cdp_per_row, rra.xff))

        if rra.steps_since_update > 0:
            if math.isnan(ds.prep.temp_val):
                self.unknown_pdps += start_pdp_offset
                self.secondary = DNAN
            else:
                self.secondary = ds.prep.temp_val

            if self.unknown_pdps > rra.cdp_per_row * rra.xff:
                debug_print("%d > %d * %10.2f" % (self.unknown_pdps, rra.cdp_per_row, rra.xff))
                self.primary = DNAN
            else:
                debug_print("primary before initialize_cdp: %10.9f" % self.primary)
                self.primary = rra.initialize_cdp_value(self, ds, start_pdp_offset)
                debug_print("primary after initialize_cdp: %10.9f" % self.primary)
            rra.carryover_cdp_value(self, ds, elapsed_steps, start_pdp_offset)

            if math.isnan(ds.prep.temp_val):
                self.unknown_pdps = ((elapsed_steps - start_pdp_offset)
                                     % rra.cdp_per_row)
                debug_print("%d = ((%d - %d) %% %d)" % (self.unknown_pdps, elapsed_steps, start_pdp_offset, rra.cdp_per_row))
            else:
                debug_print("resetting unknown counter")
                self.unknown_pdps = 0
        else:
            if math.isnan(ds.prep.temp_val):
                self.unknown_pdps += elapsed_steps
            else:
                self.value = rra.calculate_cdp_value(self, ds, elapsed_steps)

        self.save(force_update=True)

    def reset(self, ds, elapsed_steps):
        debug_print("->reset_cdp")
        self.primary = ds.prep.temp_val
        self.secondary = ds.prep.temp_val
        self.save(force_update=True)
