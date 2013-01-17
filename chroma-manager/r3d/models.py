#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import time
#from datetime import datetime
#from dateutil.tz import tzutc, tzlocal
import math
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from r3d.exceptions import BadUpdateString, BadUpdateTime
import r3d
from r3d.lib import DNAN, DINF, debug_print

# Don't want a try/except block to fall back to slow pickle.
# If we can't use cPickle, then we're going to have problems!
import cPickle as pickle
from cPickle import UnpicklingError

try:
    from psycopg2 import Binary
    pg_binary_cls = type(Binary(''))
except ImportError:
    pass


class PickledObjectField(models.Field):
    """
    A field which automatically pickles on save and unpickles on load.
    Uses MEDIUMBLOB on MySQL (max field size 16MB).
    """
    __metaclass__ = models.SubfieldBase

    def to_python(self, value):
        try:
            return pickle.loads(str(value))
        except UnpicklingError:
            return value

    def get_prep_value(self, value):
        from django.db import connection
        pickled_cls = str
        if 'postgresql' in connection.settings_dict['ENGINE']:
            pickled_cls = pg_binary_cls

        if value is not None and not isinstance(value, pickled_cls):
            # NB: Binary pickle doesn't play well with field types
            # that expect to work with strings (i.e. have a character
            # encoding).  On MySQL, we want to use a BLOB type.
            value = pickle.dumps(value, pickle.HIGHEST_PROTOCOL)
            if pickled_cls != str:
                value = Binary(value)
        elif isinstance(value, pickled_cls):
            # Bit of belt-and-suspenders here...  It's reasonably safe to
            # assume that we wouldn't knowingly define a string-like field
            # as a PickledObjectField.  We don't want to pickle an
            # already-pickled value, though.
            raise RuntimeError("%s: already pickled?" % self.name)
        return value

    def db_type(self, connection):
        if connection.settings_dict['ENGINE'] == 'django.db.backends.mysql':
            # Performance-wise, there's no appreciable difference between
            # BLOB and MEDIUMBLOB.  We're not doing any kind of indexing
            # or queries on the pickle columns, so it's probably best to
            # go with the safer option to keep our pickles from being
            # truncated (we wouldn't want that, would we?).
            #
            # 2^16 bytes == 65KB
            #return 'BLOB'
            # 2^24 bytes == 16MB
            return 'MEDIUMBLOB'
            # 2^32 bytes == 4GB
            #return 'LONGBLOB'
        elif 'postgresql' in connection.settings_dict['ENGINE']:
            # variable-length binary string
            return 'bytea'
        else:
            # generic default
            return 'TEXTFIELD'

    def get_prep_lookup(self, lookup_type, value):
        if lookup_type == "exact":
            value = self.get_prep_value(value)
            return super(PickledObjectField, self).get_prep_lookup(lookup_type, value)
        elif lookup_type == "in":
            value = [self.get_prep_value(v) for v in value]
            return super(PickledObjectField, self).get_prep_lookup(lookup_type, value)
        else:
            raise TypeError("Lookup type %s is not supported." % lookup_type)


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

    name = models.CharField(max_length=255, unique=True)
    start = models.BigIntegerField(default=lambda: Database.default_start())
    step = models.BigIntegerField(default=300)
    last_update = models.BigIntegerField(blank=True)
    ds_pickle = PickledObjectField(null=True)
    prep_pickle = PickledObjectField(null=True)
    rra_pointers = PickledObjectField(null=True)

    # Leverage the ContentTypes framework to allow R3D databases to be
    # optionally associated with other apps' models.
    content_type = models.ForeignKey(ContentType, null=True)
    object_id = models.PositiveIntegerField(null=True)
    content_object = generic.GenericForeignKey('content_type', 'object_id')

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
        if "start" in kwargs:
            kwargs['start'] = self._parse_time(kwargs['start'])

        super(Database, self).__init__(*args, **kwargs)

        self.cache_lists_and_check_pickles()

    def available_resolutions(self):
        """
        Returns a list of resolutions, in seconds, available for query.
        By default, the highest-resolution archive which best matches the
        query window is used to provide datapoints, but a lower resolution
        can be specified if desired.
        """
        return [rra.cdp_per_row * self.step
                for rra in self.archives.order_by('cdp_per_row')]

    def cache_lists_and_check_pickles(self):
        self.ds_list = list(self.datasources.all().order_by('id'))
        self.rra_list = list(self.archives.all().order_by('id'))

        if self.pk is not None:
            if self.ds_pickle is None:
                self.rebuild_ds_pickle()

            if self.prep_pickle is None:
                self.rebuild_prep_pickle()

            if self.rra_pointers is None:
                self.rebuild_rra_pointers()

    def rebuild_rra_pointers(self, force=False):
        if force or self.rra_pointers is None:
            self.rra_pointers = {}
            for rra in self.rra_list:
                self.rra_pointers[rra.pk] = {'wrapped': False, 'slot': 0}

    def rebuild_ds_pickle(self, force=False):
        if force or self.ds_pickle is None:
            self.ds_pickle = {}

        unknown_seconds = self.last_update % self.step
        self.ds_list = list(self.datasources.all().order_by('id'))
        for ds in self.ds_list:
            if ds.name not in self.ds_pickle:
                self.ds_pickle[ds.name] = PdpPrep(ds.pk, unknown_seconds)

    def rebuild_prep_pickle(self, force=False):
        if force or self.prep_pickle is None:
            self.prep_pickle = {}

        if r3d.DEBUG:
            debug_print("  rebuilding prep pickle")

        # Rebuild this here because if the prep pickle needs to
        # be rebuilt this probably does too.
        self.rra_list = list(self.archives.all().order_by('id'))

        from django.db import connection
        cursor = connection.cursor()
        sql = """
SELECT rra.id, ds.id, ds.name, rra.cdp_per_row
FROM %s_archive AS rra
INNER JOIN %s_datasource AS ds
ON ds.database_id = rra.database_id
WHERE rra.database_id = %s
        """ % (self._meta.app_label, self._meta.app_label, self.pk)
        cursor.execute(sql)

        def calc_unknown_pdps(db, ds_name, cdp_per_row):
            try:
                return ((db.last_update - db.ds_pickle[ds_name].unknown_seconds)
                                        % (db.step * cdp_per_row)
                                        / db.step)
            except KeyError:
                # If this fails, it's because the ds prep hasn't been pickled
                # yet, which means that there can't be any unknown seconds
                # anyway.
                return long(0)

        for row in cursor.fetchall():
            cdp_key = tuple([row[0], row[1]])
            if cdp_key not in self.prep_pickle:
                unk_pdps = calc_unknown_pdps(self, row[2], row[3])
                self.prep_pickle[cdp_key] = CdpPrep(archive_id=row[0],
                                                    datasource_id=row[1],
                                                    unknown_pdps=unk_pdps)
                if r3d.DEBUG:
                    debug_print("  new CdpPrep for %s: %d" % (list(cdp_key),
                                                              unk_pdps))

    def save(self, *args, **kwargs):
        if not self.last_update:
            self.last_update = self.start
        #print "%s: %d ds, %d rra" % (self.name, len(self.ds_list), len(self.rra_list))
        #print "%s: %s x %s" % (self.name, [ds.id for ds in self.ds_list],
        #                                  [rra.id for rra in self.rra_list])

        new_db = self.pk is None
        super(Database, self).save(*args, **kwargs)

        # After saving a new DB, build the pickle list.  We don't
        # want or need to do this with existing DBs for performance reasons.
        if new_db:
            self.cache_lists_and_check_pickles()

        for name, prep in self.ds_pickle.items():
            if r3d.DEBUG:
                debug_print("  %s pickled %s: %s" % (hex(id(self)),
                                                     name, prep.__dict__))

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

        if r3d.DEBUG:
            debug_print("vvv--------------------------------------------------vvv")

        if len(new_values.keys()) != len(self.ds_list):
            self.rebuild_ds_pickle()
            self.rebuild_prep_pickle()
            if len(new_values.keys()) != len(self.ds_list):
                raise BadUpdateString("Update string DS count (%d) doesn't match database DS count (%d)" % (len(new_values.keys()), len(self.ds_list)))

        if interval < 1:
            raise BadUpdateTime("Illegal update time %d (minimum one second step from %d)" % (update_time, self.last_update))

        (elapsed_steps,
         pre_step_interval,
         current_step_fraction,
         pdp_count) = r3d.lib.calculate_elapsed_steps(self.last_update,
                                                      self.step,
                                                      update_time)

        # Update each DS's internal counters using the new readings.
        # TODO: Optimize this to update the pickle values directly
        for ds in self.ds_list:
            ds.add_new_reading(self, new_values[ds.name], update_time,
                               interval)

        if elapsed_steps == 0:
            # If we haven't crossed a step threshold, then we don't
            # want to consolidate any datapoints.  Just update the DS
            # scratch counters.
            if r3d.DEBUG:
                debug_print("  simple update")
            self.simple_update(update_time, interval)
        else:
            # If we have crossed one (or more) step thresholds, then
            # we need to run through and consolidate all DS PDPs.
            if r3d.DEBUG:
                debug_print("  consolidation needed")
            r3d.lib.consolidate_all_pdps(self,
                                         interval,
                                         elapsed_steps,
                                         pre_step_interval,
                                         current_step_fraction,
                                         pdp_count)

        self.last_update = update_time
        self.save(force_update=True)

        if r3d.DEBUG:
            debug_print("^^^--------------------------------------------------^^^")

    def simple_update(self, update_time, interval):
        for ds_name, prep in self.ds_pickle.items():
            if math.isnan(prep.new_val):
                prep.unknown_seconds += math.floor(interval)
            else:
                if math.isnan(prep.scratch):
                    prep.scratch = prep.new_val
                else:
                    prep.scratch += prep.new_val

            if r3d.DEBUG:
                debug_print("  %s scratch %lf, unknown %lu" %
                            (ds_name, prep.scratch, prep.unknown_seconds))

    def parse_update_dict(self, update, missing_ds_block=None):
        standard_update = {}

        # First, get new readings for all of the DSes we know about.
        for ds in self.ds_list:
            try:
                ds_update = update.pop(ds.name)
                # handle either style of update dict
                try:
                    standard_update[ds.name] = ds_update['value']
                except TypeError:
                    standard_update[ds.name] = ds_update
            except KeyError:
                # no news is still news
                standard_update[ds.name] = DNAN

        # Now, if there's anything left over, we'll let the caller create
        # DS/RRA entries, if it bothered to try.
        if len(update.keys()) > 0:
            if r3d.DEBUG:
                debug_print("  leftover updates: %s" % update.keys())
            if missing_ds_block:
                for new_ds_name in update.keys():
                    missing_ds_block(self, new_ds_name, update[new_ds_name])

            # Rebuild pickles to account for new DS
            self.rebuild_ds_pickle()
            self.rebuild_prep_pickle()

            for new_ds_name in update.keys():
                if new_ds_name in self.ds_pickle:
                    ds_update = update.pop(new_ds_name)
                    try:
                        standard_update[new_ds_name] = ds_update['value']
                    except TypeError:
                        standard_update[new_ds_name] = ds_update
                else:
                    raise ValueError("Unknown metrics: %s" % update.keys())

        return standard_update

    def update(self, updates, missing_ds_block=None):
        """
        Receives either:
        an RRD-style update string (update_time:ds_val_0..ds_val_N)
        or a dict containing one or more update dicts {time: {ds_name: ds_val, ...}}
        and updates the corresponding DS PDPs/CDPs.

        No return value.
        """
        if hasattr(updates, "partition"):
            # TODO: This is legacy cruft and terribly inefficient.
            # The tests rely on being able to supply rrdtool-style update
            # strings, though.  Need to update them at some point.
            update_time, update_vals = r3d.lib.parse_update_string(updates)
            ds_names = [ds.name for ds in self.datasources.all().order_by('id')]
            new_readings = dict(zip(ds_names, update_vals))
            self.single_update(update_time, new_readings)
        else:
            for update in sorted(updates.keys()):
                new_readings = self.parse_update_dict(updates[update],
                                                      missing_ds_block)
                self.single_update(self._parse_time(update), new_readings)

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

        return r3d.lib.fetch_best_rra_rows(self,
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

        for ds_name, prep in self.ds_pickle.items():
            if fetch_metrics is None or ds_name in fetch_metrics:
                # Convert NaN -> None for consumers (HYD-985)
                results[ds_name] = (None if math.isnan(prep.last_reading)
                                         else prep.last_reading)

        return (self.last_update, results)


# http://djangosnippets.org/snippets/2408/
# Grumble.
class PoorMansStiModel(models.Model):
    classes = dict()
    mod = models.CharField(max_length=50)
    cls = models.CharField(max_length=30)

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        super(PoorMansStiModel, self).__init__(*args, **kwargs)
        if self.cls:
            if not self.cls in PoorMansStiModel.classes:
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
    database = models.ForeignKey(Database, related_name="datasources")
    name = models.CharField(max_length=255)
    heartbeat = models.BigIntegerField()
    min_reading = SciFloatField(null=True, blank=True)
    max_reading = SciFloatField(null=True, blank=True)

    class Meta:
        unique_together = ("database", "name")

    def transform_reading(self, db, value, update_time, interval):
        return value

    def add_new_reading(self, db, new_reading, update_time, interval):
        if r3d.DEBUG:
            debug_print("  anr %s top: %s" %
                        (self.name, db.ds_pickle[self.name].__dict__))
        # stash this for debugging
        saved_last = db.ds_pickle[self.name].last_reading

        if self.heartbeat < interval:
            db.ds_pickle[self.name].last_reading = DNAN

        if math.isnan(new_reading) or self.heartbeat < interval:
            db.ds_pickle[self.name].new_val = DNAN
        else:
            db.ds_pickle[self.name].new_val = self.transform_reading(db,
                                                       new_reading,
                                                       update_time,
                                                       interval)

            # Make sure that we're inside the bounds defined by the DS.
            try:
                rate = db.ds_pickle[self.name].new_val / interval
            except ZeroDivisionError:
                rate = DNAN

            if (not math.isnan(rate) and
                ((not math.isnan(self.max_reading) and
                  rate > self.max_reading)) or
                ((not math.isnan(self.min_reading) and
                  rate < self.min_reading))):
                db.ds_pickle[self.name].new_val = DNAN

        # save this for the next run
        db.ds_pickle[self.name].last_reading = new_reading

        if r3d.DEBUG:
            debug_print("  anr %s bottom: %s" %
                        (self.name, db.ds_pickle[self.name].__dict__))
            debug_print("  %s @ %d: (%.2f) %.2f -> %.2f" %
                        (self.name, update_time, saved_last, new_reading,
                         db.ds_pickle[self.name].new_val))


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

    def transform_reading(self, db, value, update_time, interval):
        if math.isnan(db.ds_pickle[self.name].last_reading) or math.isnan(value):
            return DNAN

        value -= db.ds_pickle[self.name].last_reading

        if value < 0.0:
            value += 4294967296.0  # 2^32

        if value < 0.0:
            value += 18446744069414584320.0  # 2^64-2^32

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

    def transform_reading(self, db, value, update_time, interval):
        if math.isnan(db.ds_pickle[self.name].last_reading):
            return DNAN
        else:
            return value - db.ds_pickle[self.name].last_reading


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

    def transform_reading(self, db, value, update_time, interval):
        return value * interval


class Archive(PoorMansStiModel):
    """
    An Archive represents a fixed set of rows, each containing
    time-based consolidated data points (CDPs) for associated Datasources.
    A given Archive has a specific resolution (number of primary data points
    per CDP).
    """
    # persistent record fields
    database = models.ForeignKey(Database, related_name="archives")
    xff = SciFloatField(default=0.5)
    cdp_per_row = models.BigIntegerField()
    rows = models.BigIntegerField()

    # ephemeral attributes
    steps_since_update = 0
    nan_cdps = 0

    def save(self, *args, **kwargs):
        new_rra = self.pk is None

        super(Archive, self).save(*args, **kwargs)

        if new_rra:
            self.database.rra_pointers[self.pk] = {'slot': 0, 'wrapped': False}
            # NB: This pointer value is only used for the lifetime
            # of the new .database object in this context -- it's not
            # persisted to rdbms because we would clobber the "real"
            # .database object.  Fun times.

    def calculate_cdp_value(self, cdp_prep, db, ds, elapsed_steps):
        raise RuntimeError("Method not implemented at this level")

    def initialize_cdp_value(self, cdp_prep, db, ds, start_pdp_offset):
        raise RuntimeError("Method not implemented at this level")

    def carryover_cdp_value(self, cdp_prep, db, ds, elapsed_steps, start_pdp_offset):
        raise RuntimeError("Method not implemented at this level")


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

    def calculate_cdp_value(self, cdp_prep, db, ds, elapsed_steps):
        if math.isnan(cdp_prep.value):
            return db.ds_pickle[ds.name].temp_val * elapsed_steps

        return cdp_prep.value + db.ds_pickle[ds.name].temp_val * elapsed_steps

    def initialize_cdp_value(self, cdp_prep, db, ds, start_pdp_offset):
        cum_val = 0.0 if math.isnan(cdp_prep.value) else cdp_prep.value
        cur_val = 0.0 if math.isnan(db.ds_pickle[ds.name].temp_val) else db.ds_pickle[ds.name].temp_val
        primary = ((cum_val + cur_val * start_pdp_offset) /
                   (self.cdp_per_row - cdp_prep.unknown_pdps))
        if r3d.DEBUG:
            debug_print("%10.9f = (%10.9f + %10.9f * %lu) / (%lu - %lu)" % (primary, cum_val, cur_val, start_pdp_offset, self.cdp_per_row, cdp_prep.unknown_pdps))
        return primary

    def carryover_cdp_value(self, cdp_prep, db, ds, elapsed_steps, start_pdp_offset):
        overlap_count = ((elapsed_steps - start_pdp_offset) % self.cdp_per_row)
        if overlap_count == 0 or math.isnan(db.ds_pickle[ds.name].temp_val):
            cdp_prep.value = 0
        else:
            cdp_prep.value = db.ds_pickle[ds.name].temp_val * overlap_count


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

    def calculate_cdp_value(self, cdp_prep, db, ds, elapsed_steps):
        return db.ds_pickle[ds.name].temp_val

    def initialize_cdp_value(self, cdp_prep, db, ds, start_pdp_offset):
        return db.ds_pickle[ds.name].temp_val

    def carryover_cdp_value(self, cdp_prep, db, ds, elapsed_steps, start_pdp_offset):
        overlap_count = ((elapsed_steps - start_pdp_offset) % self.cdp_per_row)
        if overlap_count == 0 or math.isnan(db.ds_pickle[ds.name].temp_val):
            cdp_prep.value = DNAN
        else:
            cdp_prep.value = db.ds_pickle[ds.name].temp_val


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

    def calculate_cdp_value(self, cdp_prep, db, ds, elapsed_steps):
        if math.isnan(cdp_prep.value):
            return db.ds_pickle[ds.name].temp_val

        return db.ds_pickle[ds.name].temp_val if (db.ds_pickle[ds.name].temp_val > cdp_prep.value) else cdp_prep.value

    def initialize_cdp_value(self, cdp_prep, db, ds, start_pdp_offset):
        cum_val = -DINF if math.isnan(cdp_prep.value) else cdp_prep.value
        cur_val = -DINF if math.isnan(db.ds_pickle[ds.name].temp_val) else db.ds_pickle[ds.name].temp_val

        if cur_val > cum_val:
            return cur_val
        else:
            return cum_val

    def carryover_cdp_value(self, cdp_prep, db, ds, elapsed_steps, start_pdp_offset):
        overlap_count = ((elapsed_steps - start_pdp_offset) % self.cdp_per_row)
        if overlap_count == 0 or math.isnan(db.ds_pickle[ds.name].temp_val):
            cdp_prep.value = -DINF
        else:
            cdp_prep.value = db.ds_pickle[ds.name].temp_val


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

    def calculate_cdp_value(self, cdp_prep, db, ds, elapsed_steps):
        if math.isnan(cdp_prep.value):
            return db.ds_pickle[ds.name].temp_val

        return db.ds_pickle[ds.name].temp_val if (db.ds_pickle[ds.name].temp_val < cdp_prep.value) else cdp_prep.value

    def initialize_cdp_value(self, cdp_prep, db, ds, start_pdp_offset):
        cum_val = DINF if math.isnan(cdp_prep.value) else cdp_prep.value
        cur_val = DINF if math.isnan(db.ds_pickle[ds.name].temp_val) else db.ds_pickle[ds.name].temp_val

        if cur_val < cum_val:
            return cur_val
        else:
            return cum_val

    def carryover_cdp_value(self, cdp_prep, db, ds, elapsed_steps, start_pdp_offset):
        overlap_count = ((elapsed_steps - start_pdp_offset) % self.cdp_per_row)
        if overlap_count == 0 or math.isnan(db.ds_pickle[ds.name].temp_val):
            cdp_prep.value = DINF
        else:
            cdp_prep.value = db.ds_pickle[ds.name].temp_val


class ArchiveRow(models.Model):
    archive_id = models.IntegerField()
    slot = models.BigIntegerField(default=0)
    ds_pickle = PickledObjectField(null=True)

    def __init__(self, *args, **kwargs):
        super(ArchiveRow, self).__init__(*args, **kwargs)

        if self.ds_pickle is None:
            self.ds_pickle = {}

    def _get_db_prepped_value(self, field_name):
        meta = self.__class__._meta
        try:
            field = [f for f in meta.local_fields if f.name == field_name][0]
        except IndexError:
            return RuntimeError("Can't find Field for %s" % field_name)

        return field.get_prep_value(field.pre_save(self, True))

    def save(self, *args, **kwargs):
        self._meta = self.__class__._meta
        # Bit of a hack; have to let the field diddle itself to get a
        # db-safe value.
        prepped_pickle = self._get_db_prepped_value("ds_pickle")

        from django.db import connection, transaction
        cursor = connection.cursor()
        if 'mysql' in connection.settings_dict['ENGINE']:
            sql = """
INSERT INTO %s_archiverow (archive_id, slot, ds_pickle)
VALUES(%%s, %%s, %%s)
ON DUPLICATE KEY UPDATE
  archive_id=VALUES(archive_id),
  slot=VALUES(slot),
  ds_pickle=VALUES(ds_pickle)
            """ % (self._meta.app_label)
            params = [self.archive_id, self.slot, prepped_pickle]
            cursor.execute(sql, params)
        elif 'postgres' in connection.settings_dict['ENGINE']:
            from itertools import repeat
            # Somewhat racy, but probably OK since we've only got one
            # process throwing metrics at the DB.  Apparently upserts are
            # hard, so pgsql doesn't handle them.
            # Cribbed from http://stackoverflow.com/a/6527838/204920
            sql = """
UPDATE %s_archiverow SET ds_pickle=%%s WHERE archive_id=%%s AND slot=%%s;
INSERT INTO %s_archiverow (archive_id, slot, ds_pickle)
    SELECT %%s, %%s, %%s
    WHERE NOT EXISTS (SELECT 1 FROM %s_archiverow
                      WHERE archive_id=%%s AND slot=%%s);
            """ % tuple(repeat(self._meta.app_label, 3))
            params = [prepped_pickle, self.archive_id, self.slot,
                      self.archive_id, self.slot, prepped_pickle,
                      self.archive_id, self.slot]
            cursor.execute(sql, params)
        else:
            raise RuntimeError("Unsupported DB: %s" % connection.settings_dict['ENGINE'])
        transaction.commit_unless_managed()


class CdpPrep(object):
    """
    Provides temporary storage for data points during the consolidation
    process.
    """
    def __init__(self, archive_id, datasource_id, unknown_pdps=long(0)):
        self.archive_id = archive_id
        self.datasource_id = datasource_id

        self.value = DNAN
        self.primary = 0.0
        self.secondary = 0.0
        self.unknown_pdps = long(unknown_pdps)


class PdpPrep(object):
    """
    Provides temporary storage for data points prior to the consolidation
    process.
    """
    def __init__(self, datasource_id, unknown_seconds=long(0)):
        self.datasource_id = datasource_id

        self.last_reading = DNAN
        self.scratch = 0.0
        self.unknown_seconds = long(unknown_seconds)
        self.new_val = DNAN
        self.temp_val = DNAN
