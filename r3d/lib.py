## Copyright 2011 Whamcloud, Inc.
## Authors: Michael MacDonald <mjmac@whamcloud.com>

import math, time
from r3d.exceptions import *

DNAN  = float('nan')
DINF  = float('inf')
DEBUG = False

def debug_print(string, end="\n"):
    if DEBUG:
        print "%s%s" % (string, end),

def parse_update_time(time_string):
    """
    Parse an incoming string for valid time values.  Returns an int
    representing seconds since the epoch (NB: precision >= 1sec).  The
    special value "N" will be interpreted as "now".
    """
    if time_string == "N":
        return int(time.time())
    else:
        try:
            return int(float(time_string))
        except ValueError:
            raise BadUpdateString, "Can't parse time from '%s'" % time_string

def parse_ds_vals(ds_string):
    """
    Parse an incoming string for DS values.  Returns a tuple containing
    ds reading values.  Unknown or missing values are entered as None.
    """
    def fixup(v):
        if v == "" or v == "U":
            return "NaN"
        else:
            return v

    try:
        return [float(fixup(val)) for val in ds_string.split(":")]
    except ValueError:
        raise BadUpdateString, "Can't parse ds vals from '%s'" % ds_string

def parse_update_string(update_string):
    """
    Parse an incoming RRD-style update string into its constituent parts.
    Update strings must always begin with an update time specification and
    contain at least one DS reading value (which can be None).  Fields are
    colon-separated.
    """
    if "@" in update_string:
        raise BadUpdateString, "At-style time formats not supported"

    time_string, ds_string = update_string.partition(":")[::2]
    if time_string == "" or ds_string == "":
        raise BadUpdateString, "No time and/or ds vals in '%s'" % update_string

    return parse_update_time(time_string), parse_ds_vals(ds_string)

def calculate_elapsed_steps(db_last_update, db_steps, update_time, interval):
    pre_int, post_int = (0,0)
    current_pdp_age = db_last_update % db_steps
    current_pdp_start = db_last_update - current_pdp_age

    last_pdp_age = update_time % db_steps
    last_pdp_start = update_time - last_pdp_age

    if last_pdp_start > current_pdp_start:
        pre_int = last_pdp_start - db_last_update
        post_int = last_pdp_age
    else:
        pre_int = interval

    pdp_count = current_pdp_start / db_steps
    elapsed_steps = (last_pdp_start - current_pdp_start) / db_steps

    debug_print("current_pdp_age: %d current_pdp_start %d last_pdp_age %d last_pdp_start %d interval: %lf pre_int: %lf post_int: %lf" % (current_pdp_age, current_pdp_start, last_pdp_age, last_pdp_start, interval, pre_int, post_int))

    return elapsed_steps, pre_int, post_int, pdp_count

# FIXME: this could probably be completely refactored away if we move
# this logic into Datasource#transform_reading().
def simple_update(ds_list, update_time, interval):
    for ds in ds_list:
        if math.isnan(ds.pdp_temp):
            ds.unknown_seconds += math.floor(interval)
        else:
            if math.isnan(ds.last_reading):
                ds.last_reading = ds.pdp_temp
            else:
                ds.last_reading += ds.pdp_temp

        ds.save()

def process_pdp_st(ds, db_step, interval, pre_int, post_int, seconds):
    pre_unknown  = 0.0

    debug_print("pdp_new: %10.2f pdp_scratch: %10.2f" % (ds.pdp_new, ds.pdp_scratch))
    if math.isnan(ds.pdp_new):
        pre_unknown = pre_int
    else:
        if math.isnan(ds.pdp_scratch):
            ds.pdp_scratch = 0.0
        ds.pdp_scratch += ds.pdp_new / interval * pre_int

    debug_print("interval: %lf, heartbeat: %lu, step: %lu, unknown_seconds: %lu" % (interval, ds.heartbeat, db_step, ds.unknown_seconds))
    if interval > ds.heartbeat or (db_step / 2.0) < ds.unknown_seconds:
        ds.pdp_temp = DNAN
    else:
        try:
            ds.pdp_temp = ds.pdp_scratch / ((seconds - ds.unknown_seconds) - pre_unknown)
        except ZeroDivisionError:
            # Both C and Ruby handle this OK without all the flailing. :P
            ds.pdp_temp = DNAN
        debug_print("%10.2f = %10.2f / ((%d - %d) - %d)" % (ds.pdp_temp, ds.pdp_scratch, seconds, ds.unknown_seconds, pre_unknown))
            
    if math.isnan(ds.pdp_new):
        ds.unknown_seconds = math.floor(post_int)
        ds.pdp_scratch = DNAN
    else:
        ds.unknown_seconds = 0
        ds.pdp_scratch = ds.pdp_new / interval * post_int
        debug_print("%lf = %lf / %lf * %lu" % (ds.pdp_scratch, ds.pdp_new, interval, post_int))

    debug_print("in process_pdp_st:")
    debug_print("pre_int: %10.2f" % pre_int)
    debug_print("post_int: %10.2f" % post_int)
    debug_print("seconds (diff_pdp_st): %d" % seconds)
    debug_print("pdp_temp: %10.2f" % ds.pdp_temp)
    debug_print("scratch: %10.2f" % ds.pdp_scratch)

    ds.save()

def consolidate_all_pdps(db, interval, elapsed_steps, pre_int, post_int, pdp_count):
    for ds in db.ds_cache:
        process_pdp_st(ds, db.step, interval, pre_int, post_int,
                       elapsed_steps * db.step)
        debug_print("PDP UPD %s elapsed_steps %d pdp_temp %lf new_prep: %lf new_unknown_sec: %d" % (ds.name, elapsed_steps, ds.pdp_temp, ds.pdp_scratch, ds.unknown_seconds))

    for rra in db.rra_cache:
        start_pdp_offset = rra.cdp_per_row - pdp_count % rra.cdp_per_row
        if start_pdp_offset <= elapsed_steps:
            rra.steps_since_update = (elapsed_steps - start_pdp_offset) / rra.cdp_per_row + 1
        else:
            rra.steps_since_update = 0

        row_updated = False
        for ds in db.ds_cache:
            cdp_prep = [prep for prep in db.prep_cache
                        if (prep.datasource_id == ds.id
                            and prep.archive_id == rra.id)][0]

            if rra.cdp_per_row > 1:
                debug_print("%d: updating cdp counters" % rra.id)
                debug_print("cdp_prep before: %s" % cdp_prep.__dict__)
                cdp_prep.update(rra, ds, elapsed_steps, start_pdp_offset)
            else:
                debug_print("%d: no consolidation necessary" % rra.id)
                cdp_prep.primary = ds.pdp_temp
                if elapsed_steps > 2:
                    cdp_prep.reset(ds, elapsed_steps)

            debug_print("cdp_prep after: %s" % cdp_prep.__dict__)

            if rra.steps_since_update > 0:
                row_updated = True
                rra.store_ds_cdp(ds, cdp_prep)

        if row_updated:
            # FIXME: Not at all happy with this -- there must be a more clever
            # way to do it and avoid the additional DB hit.  Perhaps stash it
            # in one of the other models we can't avoid updating?
            rra.current_row += 1
            if rra.current_row >= rra.rows:
                rra.current_row = 0
            rra.save()

# FIXME: This monster needs a serious refactoring.  At some point.
def fetch_best_rra_rows(db, archive_type, start_time, end_time, step, fetch_metrics):
    best_full_rra = None
    best_part_rra = None
    best_full_step_diff = 0
    best_part_step_diff = 0
    tmp_match = 0
    best_match = 0
    first_full = 1
    first_part = 1
    start_offset = None
    end_offset = None
    real_start = start_time
    real_end = end_time
    real_step = step
    chosen_rra = None
    dp_rows = []

    debug_print("Looking for start %d end %d step %d" % (start_time, end_time, step))
    
    for rra in db.archives.filter(cls=archive_type):
        cal_end = (db.last_update -
                   (db.last_update % (rra.cdp_per_row * db.step)))
        cal_start = (cal_end - (rra.cdp_per_row * rra.rows * db.step))

        full_match = cal_end - cal_start
        debug_print("Considering start %d end %d step %d" % (cal_start, cal_end, db.step * rra.cdp_per_row), end=" ")

        tmp_step_diff = abs(step - (db.step * rra.cdp_per_row))

        if cal_start <= start_time:
            if (first_full > 0) or (tmp_step_diff < best_full_step_diff):
                first_full = 0
                best_full_step_diff = tmp_step_diff
                best_full_rra = rra
                debug_print("best full match so far")
            else:
                debug_print("full match, not best")
                pass
        else:
            tmp_match = full_match
            if cal_start > start_time:
                tmp_match -= (cal_start - start_time)

            if (first_part > 0 or (best_match < tmp_match) or
                (best_match == tmp_match and 
                 tmp_step_diff < best_part_step_diff)):
                debug_print("best partial so far")
                first_part = 0
                best_match = tmp_match
                best_part_step_diff = tmp_step_diff
                best_part_rra = rra
            else:
                debug_print("partial match, not best")
                pass

    if first_full == 0:
        chosen_rra = best_full_rra
    elif first_part == 0:
        chosen_rra = best_part_rra
    else:
        raise RuntimeError, "No RRA for CF %s" % archive_type

    real_step = db.step * chosen_rra.cdp_per_row
    real_start -= start_time % real_step
    real_end += real_step - end_time % real_step
    rows = (real_end - real_start) / real_step + 1

    debug_print("We found start %d end %d step %d rows %d" % (real_start, real_end, real_step, rows))

    rra_end_time = (db.last_update - (db.last_update % real_step))
    debug_print("%d = (%d - (%d %% %d))" % (rra_end_time, db.last_update, db.last_update, real_step))
    rra_start_time = (rra_end_time - (real_step * (chosen_rra.rows - 1)))
    debug_print("%d = (%d - (%d * (%d - 1)))" % (rra_start_time, rra_end_time, real_step, chosen_rra.rows))
    start_offset = (real_start + real_step - rra_start_time) / real_step
    end_offset = (rra_end_time - real_end) / real_step

    debug_print("rra_start %d rra_end %d start_off %d end_off %d" % (rra_start_time, rra_end_time, start_offset, end_offset))
    rra_pointer = 0
    if real_start <= rra_end_time and real_end >= (rra_start_time - real_step):
        if start_offset <= 0:
            rra_pointer = chosen_rra.current_row
        else:
            rra_pointer = chosen_rra.current_row + start_offset

        rra_pointer = rra_pointer % chosen_rra.rows
        debug_print("adjusted pointer to %d" % rra_pointer)

    results = {}
    if fetch_metrics is None:
        ds_list = db.datasources.all()
    else:
        ds_list = db.datasources.filter(name__in=fetch_metrics)
    ds_cdps = {}
    for ds in ds_list:
        ds_cdps[ds] = chosen_rra.ds_cdps(ds)

    dp_time = real_start + real_step
    for i in range(start_offset, chosen_rra.rows - end_offset):
        results[dp_time] = {}
        if i < 0:
            debug_print("pre fetch %d -- " % i, end=" ")
            for ds in ds_list:
                results[dp_time][ds.name] = DNAN
                debug_print("%10.2f" % results[dp_time][ds.name], end=" ")
        elif i >= chosen_rra.rows:
            debug_print("past fetch %d -- " % i, end=" ")
            for ds in ds_list:
                results[dp_time][ds.name] = DNAN
                debug_print("%10.2f" % results[dp_time][ds.name], end=" ")
        else:
            if rra_pointer >= chosen_rra.rows:
                rra_pointer -= chosen_rra.rows
                debug_print("wrapped")

            debug_print("post fetch %d -- " % i, end=" ")
            for ds in ds_list:
                try:
                    results[dp_time][ds.name] = ds_cdps[ds][rra_pointer].value
                except IndexError:
                    # If we didn't find the DB record, then we've hit a
                    # dead zone in the Archive rows, and we just return NaN.
                    results[dp_time][ds.name] = DNAN
                debug_print("%10.2f" % results[dp_time][ds.name], end=" ")

        debug_print("")

        dp_time += real_step
        rra_pointer += 1

    return results
