# vim:fileencoding=utf-8
# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import re
from collections import defaultdict
from chroma_core.models.conf_param import ConfParam


class ParamType(object):
    def validate(self, val):
        raise NotImplementedError

    def test_vals(self):
        raise NotImplementedError()


class IntegerParam(ParamType):
    def __init__(self, min_val=None, max_val=None):
        if min_val and max_val:
            assert max_val >= min_val

        self.min_val = min_val
        self.max_val = max_val

    def validate(self, val):
        try:
            val = int(val)
        except ValueError:
            raise ValueError("Must be an integer")

        if self.min_val is not None and val < self.min_val:
            raise ValueError("Must be greater than or equal to %s" % self.min_val)
        if self.max_val is not None and val > self.max_val:
            raise ValueError("Must be less than or equal to %s" % self.max_val)

    def test_vals(self):
        vals = []
        if self.min_val is not None:
            vals.append(self.min_val)
        if self.max_val is not None:
            vals.append(self.max_val)
        if self.min_val is None and self.max_val is None:
            vals.append(20)

        if self.max_val is not None and self.min_val is not None and (self.max_val - self.min_val > 1):
            vals.append(self.min_val + (self.max_val - self.min_val) / 2)

        return vals


class EnumParam(ParamType):
    """Value is one of self.options"""

    def __init__(self, options):
        self.options = options

    def validate(self, val):
        if not val in self.options:
            raise ValueError("Must be one of %s" % self.options)

    def test_vals(self):
        return self.options


class BooleanParam(EnumParam):
    """Value is 0 or 1"""

    def __init__(self):
        super(BooleanParam, self).__init__(options=["0", "1"])


class BytesParam(ParamType):
    """A size in bytes, written with a unit letter at the end in the format supported
    by lprocfs_write_frac_u64.  e.g. "40m", "20G".  Valid postfixes are [ptgmkPTGMK].

    If units attribute is non-null, this just stores an integer, i.e. for settings
    where the unit is built into the name of the setting.  Use BytesParam instead of
    integerparam so that for presentation it is possible to display "40MB" instead of
    just displaying "40" and leaving it to the user to notice that the setting ends _mb."""

    def __init__(self, units=None, min_val=None, max_val=None):
        self.min_val = min_val
        self.max_val = max_val

        # Check we don't have a lower bound bigger than the upper
        if self.min_val is not None and self.max_val is not None:
            assert self._str_to_bytes(self.min_val) <= self._str_to_bytes(self.max_val)

        # Check that units is something like 'm' or 'G'
        if units is not None:
            if not len(units) == 1:
                raise RuntimeError()
            if not units in "ptgmkPTGMK":
                raise RuntimeError()
        self.units = units

    def test_vals(self):
        vals = []
        if self.min_val:
            vals.append(self.min_val)
        if self.max_val:
            vals.append(self.max_val)

        if self.max_val is None and self.min_val is None:
            if self.units:
                vals.append("20%s" % self.units)
            else:
                vals.append("20m")

        return vals

    def _str_to_bytes(self, val):
        units = 1
        postfixes = {"p": 1 << 100000, "t": 1 << 10000, "g": 1 << 1000, "m": 1 << 100, "k": 1 << 10}
        try:
            units = postfixes[val[-1:].lower()]
            number = val[0:-1]
        except KeyError:
            units = 1
            number = val

        real_val = float(number)
        real_val *= units

        return real_val

    def validate(self, val):
        if self.units:
            if not re.match("^\d+$", val):
                raise ValueError("Invalid size string (must be integer number of %s)" % self.units)
            bytes_val = self._str_to_bytes(val + self.units)
        else:
            if not re.match("^\d+(\.\d+)?[ptgmkPTGMK]?$", val):
                raise ValueError("Invalid size string" % val)
            bytes_val = self._str_to_bytes(val)

        if self.min_val and bytes_val < self._str_to_bytes(self.min_val):
            raise ValueError("Must be at least %s bytes" % self.min_val)
        if self.max_val and bytes_val > self._str_to_bytes(self.max_val):
            raise ValueError("Must be at most %s bytes" % self.max_val)


class PercentageParam(IntegerParam):
    def __init__(self):
        super(PercentageParam, self).__init__(min_val=0, max_val=100)

    def validate(self, val):
        try:
            super(PercentageParam, self).validate(val)
        except ValueError:
            raise ValueError("Must be an integer between 0 and 100")


from chroma_core.models import FilesystemClientConfParam, FilesystemGlobalConfParam, MdtConfParam, OstConfParam

all_params = {
    "lov.stripesize": (
        MdtConfParam,
        BytesParam(),
        'Default stripe size for the file system (specified as a value followed by a one-letter unit). Default is 4M. In the "Lustre Operations Manual", see Section 36.14: mkfs.lustre.',
    ),
    "lov.stripecount": (
        MdtConfParam,
        IntegerParam(),
        'Default stripe count for the file system. Default is 1. In the "Lustre Operations Manual", see Section 36.14: mkfs.lustre.',
    ),
    "osc.active": (
        OstConfParam,
        BooleanParam(),
        'Controls whether an OST is in or out of service. Setting Active to 0 causes the OST to be deactivated. Setting Active to 1, restores the OST to service. In the "Lustre Operations Manual", see Section 14.1.6.1: Removing an OST from the File System and Section 14.1.6.4: Returning a Deactivated OST to Service.',
    ),
    # "Free Space Distribution"
    # =========================
    "lov.qos_prio_free": (
        MdtConfParam,
        PercentageParam(),
        'Priority (value of 0 to 100) of free-space striping vs. distributing stripes across OSTs to maximize network balancing. A higher value gives more weight to free-space striping and a lower value gives more weight to balancing across OSTs. Default is 90. In the "Lustre Operations Manual", see Section 18.5.3: Adjusting the Weighting Between Free Space and Location and Section 31.1.5: Free Space Distribution.',
    ),
    # "Managing Stripe Allocation"
    # ============================
    "lov.qos_threshold_rr": (
        MdtConfParam,
        IntegerParam(min_val=0, max_val=100),
        'Priority (value of 0 to 100) of round robin (RR) stripe allocation vs. quality of service (QOS). A higher value gives more weight to RR, and a lower value gives more weight to QOS. Default is 16. In the "Lustre Operations Manual", see Section 31.1.5.1: Managing Stripe Allocation.',
    ),
    # "Lustre I/O Tunables"
    # =====================
    "llite.max_cached_mb": (
        FilesystemClientConfParam,
        BytesParam(units="m"),
        'Maximum amount of inactive data (in MB) cached by the client. Default is 75% of available RAM in MB. In the "Lustre Operations Manual", see Section 31.2: Lustre I/O Tunables.',
    ),
    # "Client I/O RPC Stream Tunables"
    # ================================
    "osc.max_dirty_mb": (
        OstConfParam,
        BytesParam(units="m", min_val="0m", max_val="512m"),
        'Amount of dirty data (0 to 512 in MBs) that can be written to and queued in the object storage client (OSC) including cached POSIX file writes. Default is 32. In the "Lustre Operations Manual", see Section 31.2.1: Client I/O RPC Stream Tunables.',
    ),
    # FIXME: this max_val is actually architecture dependent
    "osc.max_pages_per_rpc": (
        OstConfParam,
        IntegerParam(min_val=1, max_val=256),
        'Maximum number of pages included in a single RPC I/O to the OST. Default minimum is a single page and default maximum is platform dependent (typically the equivalent of about 1 MB). In the "Lustre Operations Manual", see Section 31.2.1: Client I/O RPC Stream Tunables.',
    ),
    "osc.max_rpcs_in_flight": (
        OstConfParam,
        IntegerParam(min_val=1, max_val=32),
        'Maximum number (from 1 to 256) of RPCs being sent concurrently from an OSC to an OST. Default is 8. In the "Lustre Operations Manual", see Section 31.2.1: Client I/O RPC Stream Tunables.',
    ),
    # "Tuning file Readahead"
    # =======================
    "llite.max_read_ahead_mb": (
        FilesystemClientConfParam,
        BytesParam(units="m"),
        'Maximum amount of data (in MB) that is read into memory when the readahead conditions are met. Default is 40. In the "Lustre Operations Manual", see Section 31.2.7: Using File Readahead and Directory Statahead.',
    ),
    "llite.max_read_ahead_whole_mb": (
        FilesystemClientConfParam,
        BytesParam(units="m"),
        'Maximum size (in MB) of a file that is read in its entirety, when the read ahead algorithm is triggered. Default is 2 MB. In the "Lustre Operations Manual", see Section 31.2.7.1: Tuning File Readahead.',
    ),
    # "Tuning directory statahead"
    # ============================
    "llite.statahead_max": (
        FilesystemClientConfParam,
        IntegerParam(min_val=0, max_val=8192),
        'Maximum number of files that can be pre-fetched by the statahead thread. Default is 32. Set to 0 to disable. In the "Lustre Operations Manual", see Section 31.2.7.2: Tuning Directory Statahead.',
    ),
    # "Using OSS Read Cache"
    # ======================
    # NB these ost.* names correspond to obdfilter.* set_param names
    "ost.read_cache_enable": (
        OstConfParam,
        BooleanParam(),
        'Controls whether data read from disk during a read request is kept in memory and available for later read requests for the same data. Default is 1 (read cache enabled). In the "Lustre Operations Manual", see Section: 31.2.8.1. Using OSS Read Cache.',
    ),
    "ost.writethrough_cache_enable": (
        OstConfParam,
        BooleanParam(),
        'Controls whether data sent to the OSS as a write request is kept in the read cache for later reads or is discarded from the cache when the write is completed. Default is 1 (writethrough cache enabled). In the "Lustre Operations Manual", see Section 31.2.8.1: Using OSS Read Cache.',
    ),
    "ost.readcache_max_filesize": (
        OstConfParam,
        BytesParam(),
        'Maximum size of a file (specified as value followed by a one-letter unit) that will be kept in memory for reads or writes by either the read cache or writethrough cache. Default is "unlimited". In the "Lustre Operations Manual", see Section 31.2.8.1: Using OSS Read Cache.',
    ),
    # OSS Asynchronous Journal Commit
    # ===============================
    "ost.sync_journal": (
        OstConfParam,
        BooleanParam(),
        'Controls whether a journal flush is forced after a bulk write or not. Default is 0, which enables the asynchronous journal commit feature to synchronously write data to disk without forcing a journal flush. In the "Lustre Operations Manual", see Section 31.2.9: OSS Asynchronous Journal Commit.',
    ),
    "ost.sync_on_lock_cancel": (
        OstConfParam,
        EnumParam(["always", "blocking", "never"]),
        'Controls if a journal is flushed or not when a lock is cancelled. Values are "always", "blocking", or "never". Default is "never". In the "Lustre Operations Manual", see Section 31.2.9: OSS Asynchronous Journal Commit.',
    ),
    # mballoc3 Tunables
    # =================
    # XXX: these don't seem to be here?  Manual bug?
    # 'Locking'
    # =========
    # XXX: Lustre does not let us conf_Param lru_size
    # http://www.mail-archive.com/lustre-discuss@lists.lustre.org/msg05278.html
    # https://bugzilla.lustre.org/show_bug.cgi?id=21084
    # TODO: I can't see how to build the conf_param path for ldlm.services.ldlm_canceld and ldlm.services.ldlm_cbd
    # "Configuring adapative timeouts"
    # ================================
    "sys.at_min": (
        FilesystemGlobalConfParam,
        IntegerParam(),
        'Adaptive timeout lower-limit or minimum processing time reported by a server (in seconds). Default is 0. In the "Lustre Operations Manual", see Section 31.1.3.1: Configuring Adaptive Timeouts.',
    ),
    "sys.at_max": (
        FilesystemGlobalConfParam,
        IntegerParam(),
        'Adaptive timeout upper-limit (in seconds). Default is 600. Set to 0 to disable adaptive timeouts. In the "Lustre Operations Manual", see Section 31.1.3.1. Configuring Adaptive Timeouts.',
    ),
    "sys.at_history": (
        FilesystemGlobalConfParam,
        IntegerParam(),
        'Time period (in seconds) within which adaptive timeouts remember the slowest event that occurred. Default is 600. In the "Lustre Operations Manual", see Section 31.1.3.1: Configuring Adaptive Timeouts.',
    ),
    "sys.at_early_margin": (
        FilesystemGlobalConfParam,
        IntegerParam(),
        'Time (in seconds) in advance of a queued request timeout at which the server sends a request to the client to extend the timeout time. Default is 5. In the "Lustre Operations Manual", see Section 31.1.3.1: Configuring Adaptive Timeouts.',
    ),
    "sys.at_extra": (
        FilesystemGlobalConfParam,
        IntegerParam(),
        'Incremental time (in seconds) that a server requests the client to add to the timeout time when the server determines that a queued request is about to time out. Default is 30. In the "Lustre Operations Manual", see Section 31.1.3.1: Configuring Adaptive Timeouts.',
    ),
    # ldlm_enqueue_min does not appear to be conf_param'able
    #'sys.ldlm_enqueue_min': (FilesystemGlobalConfParam, IntegerParam(), "Sets the minimum lock enqueue time. Default value is 100. The ldlm_enqueue  time is the maximum of the measured enqueue estimate (influenced by at_min and at_max parameters), multiplied by a weighting factor, and the ldlm_enqueue_min setting. LDLM lock enqueues were based on the obd_timeout  value; now they have a dedicated minimum value. Lock enqueues increase as the measured enqueue times increase (similar to adaptive timeouts)."),
    # "Lustre Timeouts"
    # =================
    "sys.timeout": (
        FilesystemGlobalConfParam,
        IntegerParam(),
        'Time (in seconds) that a client waits for a server to complete an RPC. Default is 100. In the "Lustre Operations Manual", see Section 31.1.2: Lustre Timeouts and Section 31.1.3: Adaptive Timeouts.',
    ),
    "sys.ldlm_timeout": (
        FilesystemGlobalConfParam,
        IntegerParam(),
        'Time (in seconds) that a server will wait for a client to reply to an initial AST (lock cancellation request). Default is 20 for an OST and 6 for an MDT. In the "Lustre Operations Manual", see Section 31.1.2: Lustre Timeouts.',
    ),
    # "Setting MDS and OSS Thread Counts"
    # ===================================
    # NB: there is also a 'thread_started' param here which is read only
    "mdt.MDS.mds.threads_min": (
        MdtConfParam,
        IntegerParam(),
        'Minimum thread count on metadata server. Default is set dynamically depending on RAM and CPU resources available on the server. In the "Lustre Operations Manual", see Section 25.1: Optimizing the Number of Service Threads and Section 31.2.13: Setting MDS and OSS Thread Counts.',
    ),
    "mdt.MDS.mds.threads_max": (
        MdtConfParam,
        IntegerParam(),
        'Maximum thread count on a metadata server. Default is set dynamically depending on RAM and CPU resources available on the server. In the "Lustre Operations Manual", see Section 25.1: Optimizing the Number of Service Threads and Section 31.2.13: Setting MDS and OSS Thread Counts.',
    ),
    "mdt.MDS.mds_readpage.threads_min": (
        MdtConfParam,
        IntegerParam(),
        'Minimum thread count on metadata server for readdir() operations. Default is set dynamically depending on RAM and CPU resources available on the server. In the "Lustre Operations Manual", see Section 25.1: Optimizing the Number of Service Threads and Section 31.2.13: Setting MDS and OSS Thread Counts.',
    ),
    "mdt.MDS.mds_readpage.threads_max": (
        MdtConfParam,
        IntegerParam(),
        'Maximum thread count on metadata server for readdir() operations. Default is set dynamically depending on RAM and CPU resources available on the server. In the "Lustre Operations Manual", see Section 25.1: Optimizing the Number of Service Threads and Section 31.2.13: Setting MDS and OSS Thread Counts.',
    ),
    "mdt.MDS.mds_setattr.threads_min": (
        MdtConfParam,
        IntegerParam(),
        'Minimum thread count on metadata server for setattr() operations. Default is set dynamically depending on RAM and CPU resources available on the server. In the "Lustre Operations Manual", see Section 25.1: Optimizing the Number of Service Threads and Section 31.2.13: Setting MDS and OSS Thread Counts.',
    ),
    "mdt.MDS.mds_setattr.threads_max": (
        MdtConfParam,
        IntegerParam(),
        'Maximum thread count on metadata server for setattr() operations. Default is set dynamically depending on RAM and CPU resources available on the server. In the "Lustre Operations Manual", see Section 25.1: Optimizing the Number of Service Threads and Section 31.2.13: Setting MDS and OSS Thread Counts.',
    ),
    "ost.OSS.ost.threads_min": (
        OstConfParam,
        IntegerParam(),
        'Minimum thread count on object storage server. Default is set dynamically depending on RAM and CPU resources available on the server. In the "Lustre Operations Manual", see Section 25.1: Optimizing the Number of Service Threads and Section 31.2.13: Setting MDS and OSS Thread Counts.',
    ),
    "ost.OSS.ost.threads_max": (
        OstConfParam,
        IntegerParam(),
        'Maximum thread count on object storage server. Default is set dynamically depending on RAM and CPU resources available on the server. In the "Lustre Operations Manual", see Section 25.1: Optimizing the Number of Service Threads and Section 31.2.13: Setting MDS and OSS Thread Counts.',
    ),
    "ost.OSS.ost_io.threads_min": (
        OstConfParam,
        IntegerParam(),
        'Minimum thread count on object storage server for bulk data I/O. Default is set dynamically depending on RAM and CPU resources available on the server. In the "Lustre Operations Manual", see Section 25.1: Optimizing the Number of Service Threads and Section 31.2.13: Setting MDS and OSS Thread Counts.',
    ),
    "ost.OSS.ost_io.threads_max": (
        OstConfParam,
        IntegerParam(),
        'Maximum thread count on object storage server for bulk data I/O. Default is set dynamically depending on RAM and CPU resources available on the server. In the "Lustre Operations Manual", see Section 25.1: Optimizing the Number of Service Threads and Section 31.2.13: Setting MDS and OSS Thread Counts.',
    ),
    "ost.OSS.ost_create.threads_min": (
        OstConfParam,
        IntegerParam(),
        'Minimum thread count on object storage server for object pre-creation operations. Default is set dynamically depending on RAM and CPU resources available on the server. In the "Lustre Operations Manual", see Section 25.1: Optimizing the Number of Service Threads and Section 31.2.13: Setting MDS and OSS Thread Counts.',
    ),
    "ost.OSS.ost_create.threads_max": (
        OstConfParam,
        IntegerParam(),
        'Maximum thread count on object storage server for object pre-creation operations. Default is set dynamically depending on RAM and CPU resources available on the server. In the "Lustre Operations Manual", see Section 25.1: Optimizing the Number of Service Threads and Section 31.2.13: Setting MDS and OSS Thread Counts.',
    ),
    # "HSM Configuration and Control"
    # =================
    "mdt.hsm_control": (
        MdtConfParam,
        EnumParam(["enabled", "shutdown", "disabled", "purge"]),
        'Controls if HSM is enabled for this MDT\'s filesystem. Values are "enabled", "shutdown", "disabled", or "purge". Default is "disabled". In the "Lustre Operations Manual", see Section XXX FIXME: HSM SOMETHING SOMETHING.',
    ),
}

_conf_param_klasses = [FilesystemClientConfParam, FilesystemGlobalConfParam, MdtConfParam, OstConfParam]
_possible_conf_params = {}

_conf_param_help = dict([(k, v[2]) for k, v in all_params.items()])


def get_conf_param_help(conf_param):
    return _conf_param_help[conf_param]


def get_possible_conf_params(klass):
    """A map of conf param name to documentation string"""
    from chroma_core.models import ManagedOst, ManagedMdt, ManagedFilesystem

    conf_param_klasses = {
        ManagedOst: (OstConfParam,),
        ManagedMdt: (MdtConfParam,),
        ManagedFilesystem: (FilesystemClientConfParam, FilesystemGlobalConfParam),
    }[klass]
    try:
        return _possible_conf_params[conf_param_klasses]
    except KeyError:
        result = dict([(k, v[2]) for k, v in all_params.items() if v[0] in conf_param_klasses])
        _possible_conf_params[conf_param_klasses] = result
        return result


def get_conf_params(obj):
    from chroma_core.models import ManagedOst, ManagedMdt, ManagedFilesystem

    if hasattr(obj, "content_type"):
        obj = obj.downcast()

    if isinstance(obj, ManagedOst):
        conf_params_query = obj.ostconfparam_set.all()
    elif isinstance(obj, ManagedMdt):
        conf_params_query = obj.mdtconfparam_set.all()
    elif isinstance(obj, ManagedFilesystem):
        import itertools

        conf_params_query = itertools.chain(
            obj.filesystemclientconfparam_set.all(), obj.filesystemglobalconfparam_set.all()
        )
    else:
        raise NotImplementedError()

    # First get explicitly set conf params
    set_conf_params = ConfParam.get_latest_params(conf_params_query)
    result = dict([(conf_param.key, conf_param.value) for conf_param in set_conf_params])
    # Then populate None for unset conf params
    for unset_conf_param in set(get_possible_conf_params(obj.__class__).keys()) ^ set(result.keys()):
        result[unset_conf_param] = None

    return result


def validate_conf_params(klass, params):
    """Return a dict of parameter name to list of human readable error strings"""
    from chroma_core.models import ManagedOst, ManagedMdt, ManagedFilesystem

    errors = defaultdict(list)
    for key, val in params.items():
        if val is None:
            continue

        if not (isinstance(val, str) or isinstance(val, unicode)):
            errors[key].append("Must be a string")
            continue

        if val.strip() != val:
            errors[key].append("May not contain leading or trailing spaces")
            continue

        try:
            model_klass, param_value_obj, help_text = all_params[key]
        except KeyError:
            errors[key].append("Unknown parameter")
        else:
            if model_klass == OstConfParam and klass != ManagedOst:
                errors[key].append("Only valid for OST")
            elif model_klass in [FilesystemClientConfParam, FilesystemGlobalConfParam] and klass != ManagedFilesystem:
                errors[key].append("Only valid for Filesystem")
            elif model_klass == MdtConfParam and klass != ManagedMdt:
                errors[key].append("Only valid for MDT")

            try:
                param_value_obj.validate(val)
            except (ValueError, TypeError) as e:
                errors[key].append(e.__str__())

    return errors


def set_conf_params(obj, params, new=True):
    from chroma_core.models import ManagedFilesystem, ManagedMdt, ManagedOst
    from chroma_core.models.target import FilesystemMember

    if isinstance(obj, ManagedFilesystem):
        mgs = obj.mgs.downcast()
    elif isinstance(obj, FilesystemMember):
        mgs = obj.filesystem.mgs.downcast()
    else:
        raise NotImplementedError

    if isinstance(obj, ManagedFilesystem):
        kwargs = {"filesystem": obj}
    elif isinstance(obj, ManagedMdt):
        kwargs = {"mdt": obj}
    elif isinstance(obj, ManagedOst):
        kwargs = {"ost": obj}
    else:
        raise NotImplementedError

    # TODO: check if the value is unchanged and return if so

    if not len(params):
        return

    param_records = []
    for key, value in params.items():
        model_klass, _, _ = all_params[key]
        existing_params = ConfParam.get_latest_params(model_klass.objects.filter(key=key, **kwargs))
        # Store if the new value is
        if (len(existing_params) > 0 and existing_params[0].value != value) or (
            len(existing_params) == 0 and value is not None
        ):
            p = model_klass(key=key, value=value, **kwargs)
            param_records.append(p)
        else:
            from chroma_api import api_log

            api_log.info("Ignoring %s %s=%s, already set" % (obj, key, value))

    if param_records:
        mgs.set_conf_params(param_records, new)
        return mgs.id
    else:
        return None


def compare(a, b):
    if set(a.keys()) != set(b.keys()):
        return False
    else:
        for k, v in a.items():
            if b[k] != v:
                return False

    return True
