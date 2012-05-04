#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import math
import time
import r3d
from r3d.exceptions import BadUpdateString, BadSearchTime

DNAN = float('nan')
DINF = float('inf')


# TODO: go through and get rid of all uses of this
def debug_print(string, end="\n"):
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
            raise BadUpdateString("Can't parse time from '%s'" % time_string)


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
        raise BadUpdateString("Can't parse ds vals from '%s'" % ds_string)


def parse_update_string(update_string):
    """
    Parse an incoming RRD-style update string into its constituent parts.
    Update strings must always begin with an update time specification and
    contain at least one DS reading value (which can be None).  Fields are
    colon-separated.
    """
    if "@" in update_string:
        raise BadUpdateString("At-style time formats not supported")

    time_string, ds_string = update_string.partition(":")[::2]
    if time_string == "" or ds_string == "":
        raise BadUpdateString("No time and/or ds vals in '%s'" % update_string)

    return parse_update_time(time_string), parse_ds_vals(ds_string)


def calculate_elapsed_steps(db_last_update, db_steps, update_time):
    """
    Calculate the interval between the last update and the current update.
    Returns a tuple containing elapsed steps, the interval in seconds
    between the last update and this one, the number of seconds past
    the current step's start time, and the number of steps since the DB's
    start time.
    """
    if r3d.DEBUG:
        debug_print("calculate_elapsed_steps(%d, %d, %d)" % (db_last_update,
                                                             db_steps,
                                                             update_time))
    # In which step was the db last updated?
    last_update_step = db_last_update - (db_last_update % db_steps)
    # How far into the current step are we?
    current_step_fraction = update_time % db_steps
    # When did the current step start?
    current_step_start = update_time - current_step_fraction

    if current_step_start > last_update_step:
        pre_step_interval = current_step_start - db_last_update
    else:
        pre_step_interval = update_time - db_last_update
        current_step_fraction = 0

    pdp_count = last_update_step / db_steps
    elapsed_steps = (current_step_start - last_update_step) / db_steps

    if r3d.DEBUG:
        debug_print("  last_update_step %d current_step_fraction %d current_step_start %d pre_step_interval %d pdp_count %d elapsed_steps %d" % (last_update_step, current_step_fraction, current_step_start, pre_step_interval, pdp_count, elapsed_steps))

    return elapsed_steps, pre_step_interval, current_step_fraction, pdp_count


def process_step_pdp(ds, db, interval, pre_step_interval, current_step_fraction,
                     seconds):
    """
    Process a Datasource's PDP for the current DB step.
    """
    if r3d.DEBUG:
        debug_print("process_step_pdp(%s, %s, %d, %d, %d, %d)" % (ds.name, db.name,
                                                            interval,
                                                            pre_step_interval,
                                                            current_step_fraction,
                                                            seconds))
    ds_prep = db.ds_pickle[ds.name]
    pre_step_unknown = 0

    if r3d.DEBUG:
        debug_print("  top: %s" % ds_prep.__dict__)

    if math.isnan(ds_prep.new_val):
        pre_step_unknown = pre_step_interval
    else:
        if math.isnan(ds_prep.scratch):
            ds_prep.scratch = 0.0
        ds_prep.scratch += ds_prep.new_val / interval * pre_step_interval

    if interval > ds.heartbeat or (db.step / 2.0) < ds_prep.unknown_seconds:
        ds_prep.temp_val = DNAN
    else:
        try:
            ds_prep.temp_val = (ds_prep.scratch /
                                ((seconds - ds_prep.unknown_seconds)
                                - pre_step_unknown))
        except ZeroDivisionError:
            ds_prep.temp_val = DNAN

        if r3d.DEBUG:
            debug_print("  ds_prep.temp_val: %.2f = %.2f / ((%d - %d) - %d)" %
                        (ds_prep.temp_val, ds_prep.scratch, seconds,
                         ds_prep.unknown_seconds, pre_step_unknown))

    if math.isnan(ds_prep.new_val):
        ds_prep.unknown_seconds = long(math.floor(current_step_fraction))
        ds_prep.scratch = DNAN
    else:
        ds_prep.unknown_seconds = long(0)
        ds_prep.scratch = ds_prep.new_val / interval * current_step_fraction

        if r3d.DEBUG:
            debug_print("  ds_prep.scratch: %lf = %lf / %lf * %lu"
                        % (ds_prep.scratch, ds_prep.new_val, interval,
                           current_step_fraction))

    if r3d.DEBUG:
        debug_print("  bottom: %s" % ds_prep.__dict__)

    db.ds_pickle[ds.name] = ds_prep


def update_cdp_prep(prep, db, rra, ds, elapsed_steps, start_pdp_offset):
    if r3d.DEBUG:
        debug_print("update_cdp_prep(%s, %s, %s, %s, %d, %d)" %
                    (prep.__dict__, db.name, rra, ds, elapsed_steps,
                     start_pdp_offset))
        debug_print("  ->update: db.ds_pickle[self.name].temp_val %.2f rra.steps_since_update %d elapsed_steps %d start_pdp_offset %d rra.cdp_per_row %d xff %.2f" % (db.ds_pickle[ds.name].temp_val, rra.steps_since_update, elapsed_steps, start_pdp_offset, rra.cdp_per_row, rra.xff))

    if rra.steps_since_update > 0:
        if math.isnan(db.ds_pickle[ds.name].temp_val):
            if r3d.DEBUG:
                debug_print("  prep.unknown_pdps: %d += %d" %
                            (prep.unknown_pdps, start_pdp_offset))

            prep.unknown_pdps += start_pdp_offset
            prep.secondary = DNAN
        else:
            prep.secondary = db.ds_pickle[ds.name].temp_val

        if prep.unknown_pdps > rra.cdp_per_row * rra.xff:
            if r3d.DEBUG:
                debug_print("  %d > %.2f (%d * %.2f)" %
                            (prep.unknown_pdps, (rra.cdp_per_row * rra.xff),
                             rra.cdp_per_row, rra.xff))

            prep.primary = DNAN
        else:
            if r3d.DEBUG:
                debug_print("  %d <= %.2f (%d * %.2f)" %
                            (prep.unknown_pdps, (rra.cdp_per_row * rra.xff),
                             rra.cdp_per_row, rra.xff))
                debug_print("  primary before initialize_cdp: %10.9f" %
                            prep.primary)

            prep.primary = rra.initialize_cdp_value(prep, db, ds, start_pdp_offset)

            if r3d.DEBUG:
                debug_print("  primary after initialize_cdp: %10.9f" %
                            prep.primary)

        rra.carryover_cdp_value(prep, db, ds, elapsed_steps, start_pdp_offset)

        if math.isnan(db.ds_pickle[ds.name].temp_val):
            prep.unknown_pdps = ((elapsed_steps - start_pdp_offset)
                                 % rra.cdp_per_row)
            if r3d.DEBUG:
                debug_print("  prep.unknown_pdps: %d = ((%d - %d) %% %d)" %
                            (prep.unknown_pdps, elapsed_steps, start_pdp_offset,
                             rra.cdp_per_row))
        else:
            if r3d.DEBUG:
                debug_print("  resetting unknown counter")
            prep.unknown_pdps = 0
    else:
        if math.isnan(db.ds_pickle[ds.name].temp_val):
            prep.unknown_pdps += elapsed_steps
        else:
            prep.value = rra.calculate_cdp_value(prep, db, ds, elapsed_steps)

    db.prep_pickle[(rra.pk, ds.pk)] = prep


def reset_cdp_prep(prep, db, ds, elapsed_steps):
    if r3d.DEBUG:
        debug_print("reset_cdp_prep(%s, %s, %s, %d)" %
                    prep.__dict__, db.name, ds.name, elapsed_steps)

    prep.primary = db.ds_pickle[ds.name].temp_val
    prep.secondary = db.ds_pickle[ds.name].temp_val
    db.prep_pickle[(prep.archive_id, prep.datasource_id)] = prep


def consolidate_all_pdps(db, interval, elapsed_steps, pre_step_interval,
                         current_step_fraction, pdp_count):
    if r3d.DEBUG:
        debug_print("consolidate_all_pdps(%s, %d, %d, %d, %d, %d)" %
                    (db.name, interval, elapsed_steps, pre_step_interval,
                     current_step_fraction, pdp_count))

    for ds in db.ds_list:
        process_step_pdp(ds, db, interval, pre_step_interval,
                         current_step_fraction, elapsed_steps * db.step)

        if r3d.DEBUG:
            debug_print("  ds %s elapsed_steps %d prep.temp_val %lf new_prep: %lf new_unknown_sec: %d" % (ds.name, elapsed_steps, db.ds_pickle[ds.name].temp_val, db.ds_pickle[ds.name].scratch, db.ds_pickle[ds.name].unknown_seconds))

    for rra in db.rra_list:
        start_pdp_offset = rra.cdp_per_row - pdp_count % rra.cdp_per_row

        if r3d.DEBUG:
            debug_print("  start_pdp_offset: %d = %d - %d %% %d" %
                        (start_pdp_offset, rra.cdp_per_row, pdp_count,
                         rra.cdp_per_row))
        if start_pdp_offset <= elapsed_steps:
            rra.steps_since_update = ((elapsed_steps - start_pdp_offset)
                                      / rra.cdp_per_row + 1)
        else:
            rra.steps_since_update = 0

        for ds in db.ds_list:
            cdp_prep = db.prep_pickle[(rra.pk, ds.pk)]

            if rra.cdp_per_row > 1:
                if r3d.DEBUG:
                    debug_print("  %d: updating cdp counters" % rra.id)
                    debug_print("  cdp_prep before: %s" % cdp_prep.__dict__)

                update_cdp_prep(cdp_prep, db, rra, ds,
                                elapsed_steps, start_pdp_offset)
            else:
                if r3d.DEBUG:
                    debug_print("  %d: no consolidation necessary" % rra.id)

                cdp_prep.primary = db.ds_pickle[ds.name].temp_val

                if elapsed_steps > 2:
                    reset_cdp_prep(cdp_prep, db, ds, elapsed_steps)

            if r3d.DEBUG:
                debug_print("  cdp_prep after: %s" % cdp_prep.__dict__)

        stashed_primaries = {}
        for idx in range(0, rra.steps_since_update):
            for ds in db.ds_list:
                cdp_prep = db.prep_pickle[(rra.pk, ds.pk)]

                # When catching up, we have a choice between filling the
                # "holes" with the latest datapoint or NaNs.  Using the
                # latest datapoint results in "smeary" graphs as the
                # same datapoint value is repeated across the gap.  If we
                # use NaNs, we get breaks in the charts, but that is
                # probably preferable to made-up data.
                if r3d.EMPTY_GAPS:
                    if (rra.steps_since_update > 1
                        and idx < rra.steps_since_update - 1):
                        if idx == 0:
                            stashed_primaries[(rra.pk, ds.pk)] = cdp_prep.primary

                        if r3d.DEBUG:
                            debug_print("  storing NaN for catchup step: %d" % idx)
                        cdp_prep.primary = DNAN
                    elif rra.steps_since_update > 1:
                        cdp_prep.primary = stashed_primaries[(rra.pk, ds.pk)]

                # Optimization for times when we're playing catch-up after
                # a long period of disuse.  Rather than pointlessly storing
                # row after row of NaNs and then discarding them, we'll
                # just ignore new ones if we've already got a full set of NaN
                # rows.
                if math.isnan(cdp_prep.primary):
                    # Don't bother storing another NaN if we've already got
                    # a full set of NaNs in there.
                    if rra.nan_cdps < rra.rows:
                        rra.store_ds_cdp(ds, cdp_prep)
                    rra.nan_cdps += 1
                else:
                    # Reset the NaN counter
                    rra.nan_cdps = 0
                    rra.store_ds_cdp(ds, cdp_prep)

            # FIXME: At some point try to stash this somewhere we're already
            # updating, maybe.
            rra.current_row += 1
            if rra.current_row >= rra.rows:
                if r3d.DEBUG:
                    debug_print("wrapped")
                rra.current_row = 0

        if rra.steps_since_update > 0:
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

    if not start_time < end_time:
        raise BadSearchTime("start (%d) must be less than end (%d)!" %
                            (start_time, end_time))

    if r3d.DEBUG:
        debug_print("  Looking for start %d end %d step %d" %
                    (start_time, end_time, step))

    for rra in db.archives.filter(cls=archive_type).order_by('id'):
        cal_end = (db.last_update -
                   (db.last_update % (rra.cdp_per_row * db.step)))
        cal_start = (cal_end - (rra.cdp_per_row * rra.rows * db.step))

        full_match = cal_end - cal_start

        if r3d.DEBUG:
            debug_print("  Considering start %d end %d step %d" %
                        (cal_start, cal_end, db.step * rra.cdp_per_row), end=" ")

        tmp_step_diff = abs(step - (db.step * rra.cdp_per_row))

        if cal_start <= start_time:
            if (first_full > 0) or (tmp_step_diff < best_full_step_diff):
                first_full = 0
                best_full_step_diff = tmp_step_diff
                best_full_rra = rra

                if r3d.DEBUG:
                    debug_print("best full match so far")
            else:
                if r3d.DEBUG:
                    debug_print("full match, not best")
                pass
        else:
            tmp_match = full_match
            if cal_start > start_time:
                tmp_match -= (cal_start - start_time)

            if (first_part > 0 or (best_match < tmp_match) or
                (best_match == tmp_match and
                 tmp_step_diff < best_part_step_diff)):
                if r3d.DEBUG:
                    debug_print("best partial so far")

                first_part = 0
                best_match = tmp_match
                best_part_step_diff = tmp_step_diff
                best_part_rra = rra
            else:
                if r3d.DEBUG:
                    debug_print("partial match, not best")
                pass

    if first_full == 0:
        chosen_rra = best_full_rra
    elif first_part == 0:
        chosen_rra = best_part_rra
    else:
        raise RuntimeError("No RRA for CF %s" % archive_type)

    real_step = db.step * chosen_rra.cdp_per_row
    real_start -= start_time % real_step
    real_end += real_step - end_time % real_step
    rows = (real_end - real_start) / real_step + 1

    if r3d.DEBUG:
        debug_print("We found start %d end %d step %d rows %d" %
                    (real_start, real_end, real_step, rows))

    rra_end_time = (db.last_update - (db.last_update % real_step))

    if r3d.DEBUG:
        debug_print("  rra_end_time: %d = (%d - (%d %% %d))" %
                    (rra_end_time, db.last_update, db.last_update, real_step))

    rra_start_time = (rra_end_time - (real_step * (chosen_rra.rows - 1)))

    if r3d.DEBUG:
        debug_print("  rra_start_time: %d = (%d - (%d * (%d - 1)))" %
                    (rra_start_time, rra_end_time, real_step, chosen_rra.rows))

    start_offset = (real_start + real_step - rra_start_time) / real_step
    end_offset = (rra_end_time - real_end) / real_step

    if r3d.DEBUG:
        debug_print("rra_start %d rra_end %d start_off %d end_off %d cur_row %d" %
                    (rra_start_time, rra_end_time, start_offset, end_offset,
                     chosen_rra.current_row))
    rra_pointer = 0
    if real_start <= rra_end_time and real_end >= (rra_start_time - real_step):
        if start_offset <= 0:
            rra_pointer = chosen_rra.current_row

            if r3d.DEBUG:
                debug_print("%d = current_row" % rra_pointer)
        else:
            rra_pointer = chosen_rra.current_row + start_offset

            if r3d.DEBUG:
                debug_print("%d = current_row + start_offset" % rra_pointer)

        rra_pointer = rra_pointer % chosen_rra.rows

        if r3d.DEBUG:
            debug_print("adjusted pointer to %d" % rra_pointer)

    results = []
    if fetch_metrics is None:
        ds_list = db.ds_list
    else:
        ds_list = db.datasources.filter(name__in=fetch_metrics).order_by('id')
    ds_cdps = {}
    for ds in ds_list:
        ds_cdps[ds] = chosen_rra.ds_cdps(ds)

    # convert None -> NaN for debug output
    fn = lambda v: v or float("NaN")

    dp_time = real_start + real_step
    for i in range(start_offset, chosen_rra.rows - end_offset):
        row_results = {}
        if i < 0:
            if r3d.DEBUG:
                debug_print("pre fetch %d -- " % i, end=" ")

            for ds in ds_list:
                row_results[ds.name] = None

                if r3d.DEBUG:
                    debug_print("%.2f" % fn(row_results[ds.name]), end=" ")
        elif i >= chosen_rra.rows:
            if r3d.DEBUG:
                debug_print("past fetch %d -- " % i, end=" ")

            for ds in ds_list:
                row_results[ds.name] = None

                if r3d.DEBUG:
                    debug_print("%.2f" % fn(row_results[ds.name]), end=" ")
        else:
            if rra_pointer >= chosen_rra.rows:
                rra_pointer -= chosen_rra.rows

                if r3d.DEBUG:
                    debug_print("wrapped")

            if r3d.DEBUG:
                debug_print("post fetch %d -- " % i, end=" ")

            for ds in ds_list:
                # If we've got a full set of CDPs, we don't need to play
                # offset games.
                selector = (i if len(ds_cdps[ds]) == chosen_rra.rows
                              else rra_pointer)
                try:
                    value = ds_cdps[ds][selector].value
                    if math.isnan(value):
                        row_results[ds.name] = None
                    else:
                        row_results[ds.name] = value
                except IndexError:
                    # If we didn't find the DB record, then we've hit a
                    # dead zone in the Archive rows, and we just return None.
                    row_results[ds.name] = None

                if r3d.DEBUG:
                    debug_print("%.2f" % fn(row_results[ds.name]), end=" ")

        if r3d.DEBUG:
            debug_print("")

        # HYD-371
        # This behavior deviates from stock rrdtool behavior, but improves
        # usability.
        if dp_time <= end_time:
            results.append((dp_time, row_results))
        else:
            if r3d.DEBUG:
                debug_print("Omitting dp row after end_time (%d > %d)" % (dp_time,
                                                                         end_time))
        dp_time += real_step
        rra_pointer += 1

    return tuple(results)
