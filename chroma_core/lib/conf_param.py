# vim:fileencoding=utf-8

import re


class ParamType(object):
    def validate(self, val):
        """Opportunity for subclasses to validate and/or transform"""
        raise NotImplementedError

    def test_vals(self):
        raise NotImplementedError()


class IntegerParam(ParamType):
    def __init__(self, min_val = None, max_val = None):
        if min_val and max_val:
            assert(max_val >= min_val)

        self.min_val = min_val
        self.max_val = max_val

    def validate(self, val):
        if self.min_val != None and val < self.min_val:
            raise ValueError
        if self.max_val != None and val > self.min_val:
            raise ValueError

    def test_vals(self):
        vals = []
        if self.min_val != None:
            vals.append(self.min_val)
        if self.max_val != None:
            vals.append(self.max_val)
        if self.min_val == None and self.max_val == None:
            vals.append(20)

        if self.max_val != None and self.min_val != None and (self.max_val - self.min_val > 1):
            vals.append(self.min_val + (self.max_val - self.min_val) / 2)

        return vals


class BooleanParam(IntegerParam):
    """Value is 0 or 1"""
    def __init__(self):
        super(BooleanParam, self).__init__(min_val = 0, max_val = 1)


class EnumParam(ParamType):
    """Value is one of self.options"""
    def __init__(self, options):
        self.options = options

    def validate(self, val):
        if not val in self.options:
            raise ValueError

    def test_vals(self):
        return self.options


class BytesParam(ParamType):
    """A size in bytes, written with a unit letter at the end in the format supported
       by lprocfs_write_frac_u64.  e.g. "40m", "20G".  Valid postfixes are [ptgmkPTGMK].

       If units attribute is non-null, this just stores an integer, i.e. for settings
       where the unit is built into the name of the setting.  Use BytesParam instead of
       integerparam so that for presentation it is possible to display "40MB" instead of
       just displaying "40" and leaving it to the user to notice that the setting ends _mb."""
    def __init__(self, units = None, min_val = None, max_val = None):
        self.min_val = min_val
        self.max_val = max_val

        # Check we don't have a lower bound bigger than the upper
        if self.min_val != None and self.max_val != None:
            assert(self._str_to_bytes(self.min_val) <= self._str_to_bytes(self.max_val))

        # Check that units is something like 'm' or 'G'
        if units != None:
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

        if self.max_val == None and self.min_val == None:
            if self.units:
                vals.append("20%s" % self.units)
            else:
                vals.append("20m")

        return vals

    def _str_to_bytes(self, val):
        units = 1
        postfixes = {'p': 1 << 100000, 't': 1 << 10000, 'g': 1 << 1000, 'm': 1 << 100, 'k': 1 << 10}
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
                raise ValueError()
            bytes_val = self._str_to_bytes(val + self.units)
        else:
            if not re.match("^\d+(\.\d+)?[ptgmkPTGMK]?$", val):
                raise ValueError()
            bytes_val = self._str_to_bytes(val)

        if self.min_val and bytes_val < self._str_to_bytes(self.min_val):
            raise ValueError()
        if self.max_val and bytes_val > self._str_to_bytes(self.max_val):
            raise ValueError()


class PercentageParam(IntegerParam):
    def __init__(self):
        super(PercentageParam, self).__init__(min_val = 0, max_val = 100)

from configure.models import FilesystemClientConfParam, FilesystemGlobalConfParam, MdtConfParam, OstConfParam
all_params = {
    'lov.stripesize': (MdtConfParam, BytesParam(), "Default stripe size"),
    'lov.stripecount': (MdtConfParam, IntegerParam(), "Default stripe count"),
    'osc.active': (OstConfParam, IntegerParam(min_val = 0, max_val = 1), ""),

    # "Free Space Distribution"
    # =========================

    'lov.qos_prio_free': (MdtConfParam, PercentageParam(), """Free-space stripe weighting, as set, gives a priority of "0" to free space (versus trying to place the stripes "widely" -- nicely distributed across OSSs and OSTs to maximize network balancing). To adjust this priority (as a percentage), use the qos_prio_free proc tunable:
* Currently, the default is 90%.
* Setting the priority to 100% means that OSS distribution does not count in the weighting, but the stripe assignment is still done via weighting. If OST 2 has twice as much free space as OST 1, it is twice as likely to be used, but it is NOT guaranteed to be used.
* Also note that free-space stripe weighting does not activate until two OSTs are imbalanced by more than 20%. Until then, a faster round-robin stripe allocator is used. (The new round-robin order also maximizes network balancing.)"""),

    # "Managing Stripe Allocation"
    # ============================
    'lov.qos_threshold_rr': (MdtConfParam, IntegerParam(min_val = 0, max_val = 100), """Whether QOS or RR is used depends on the setting of the qos_threshold_rr proc tunable. The qos_threshold_rr variable specifies a percentage threshold where the use of QOS or RR becomes more/less likely. The qos_threshold_rr tunable can be set as an integer, from 0 to 100, and results in this stripe allocation behavior:
 * If qos_threshold_rr is set to 0, then QOS is always used
 * If qos_threshold_rr is set to 100, then RR is always used
 * The larger the qos_threshold_rr setting, the greater the possibility that RR is used instead of QOS"""),

    # "Lustre I/O Tunables"
    # =====================
    'llite.max_cached_mb': (FilesystemClientConfParam, BytesParam(units='m'), "This tunable is the maximum amount of inactive data cached by the client (default is 3/4 of RAM)."),

    # "Client I/O RPC Stream Tunables"
    # ================================
    'osc.max_dirty_mb': (OstConfParam, BytesParam(units = 'm', min_val = '0m', max_val = '512m'), "This tunable controls how many MBs of dirty data can be written and queued up in the OSC. POSIX file writes that are cached contribute to this count. When the limit is reached, additional writes stall until previously-cached writes are written to the server. This may be changed by writing a single ASCII integer to the file. Only values between 0 and 512 are allowable. If 0 is given, no writes are cached. Performance suffers noticeably unless you use large writes (1 MB or more)."),
    # FIXME: this max_val is actually architecture dependent
    'osc.max_pages_per_rpc': (OstConfParam, IntegerParam(min_val = 1, max_val = 256), "This tunable is the maximum number of pages that will undergo I/O in a single RPC to the OST. The minimum is a single page and the maximum for this setting is platform dependent (256 for i386/x86_64, possibly less for ia64/PPC with larger PAGE_SIZE), though generally amounts to a total of 1 MB in the RPC."),
    'osc.max_rpcs_in_flight': (OstConfParam, IntegerParam(min_val = 1, max_val = 32), "This tunable is the maximum number of concurrent RPCs in flight from an OSC to its OST. If the OSC tries to initiate an RPC but finds that it already has the same number of RPCs outstanding, it will wait to issue further RPCs until some complete. The minimum setting is 1 and maximum setting is 32. If you are looking to improve small file I/O performance, increase the max_rpcs_in_flight value."),

    # "Tuning file Readahead"
    # =======================
    'llite.max_read_ahead_mb': (FilesystemClientConfParam, BytesParam(units = 'm'), "This tunable controls the maximum amount of data readahead on a file. Files are read ahead in RPC-sized chunks (1 MB or the size of read() call, if larger) after the second sequential read on a file descriptor. Random reads are done at the size of the read() call only (no readahead). Reads to non-contiguous regions of the file reset the readahead algorithm, and readahead is not triggered again until there are sequential reads again. To disable readahead, set this tunable to 0. The default value is 40 MB."),
    'llite.max_read_ahead_whole_mb': (FilesystemClientConfParam, BytesParam(units = 'm'), "This tunable controls the maximum size of a file that is read in its entirety, regardless of the size of the read()."),


    # "Tuning directory statahead"
    # ============================
    'llite.statahead_max': (FilesystemClientConfParam, IntegerParam(min_val = 0, max_val = 8192), "This tunable controls whether directory statahead is enabled and the maximum statahead count. By default, statahead is active."),

    # "Using OSS Read Cache"
    # ======================
    # NB these ost.* names correspond to obdfilter.* set_param names
    'ost.read_cache_enable': (OstConfParam, BooleanParam(), "read_cache_enable controls whether data read from disk during a read request is kept in memory and available for later read requests for the same data, without having to re-read it from disk. By default, read cache is enabled (read_cache_enable = 1)."),
    'ost.writethrough_cache_enable': (OstConfParam, BooleanParam(), "writethrough_cache_enable controls whether data sent to the OSS as a write request is kept in the read cache and available for later reads, or if it is discarded from cache when the write is completed. By default, writethrough cache is enabled (writethrough_cache_enable = 1)."),
    'ost.readcache_max_filesize': (OstConfParam, BytesParam(), "readcache_max_filesize controls the maximum size of a file that both the read cache and writethrough cache will try to keep in memory. Files larger than readcache_max_filesize will not be kept in cache for either reads or writes."),

    # OSS Asynchronous Journal Commit
    # ===============================

    'ost.sync_journal': (OstConfParam, BooleanParam(), "To enable asynchronous journal commit, set the sync_journal parameter to zero (sync_journal=0)"),
    'ost.sync_on_lock_cancel': (OstConfParam, EnumParam(['always', 'blocking', 'never']), """When asynchronous journal commit is used, clients keep a page reference until the journal transaction commits. This can cause problems when a client receives a blocking callback, because pages need to be removed from the page cache, but they cannot be removed because of the extra page reference.
This problem is solved by forcing a journal flush on lock cancellation. When this happens, the client is granted the metadata blocks that have hit the disk, and it can safely release the page reference before processing the blocking callback. The parameter which controls this action is sync_on_lock_cancel, which can be set to the following values:
• always: Always force a journal flush on lock cancellation
• blocking: Force a journal flush only when the local cancellation is due to a blocking callback
• never: Do not force any journal flush"""),


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

'sys.at_min': (FilesystemGlobalConfParam, IntegerParam(), "Sets the minimum adaptive timeout (in seconds). Default value is 0. The at_min parameter is the minimum processing time that a server will report. Clients base their timeouts on this value, but they do not use this value directly. If you experience cases in which, for unknown reasons, the adaptive timeout value is too short and clients time out their RPCs (usually due to temporary network outages), then you can increase the at_min value to compensate for this. Ideally, users should leave at_min set to its default."),
'sys.at_max': (FilesystemGlobalConfParam, IntegerParam(), """Sets the maximum adaptive timeout (in seconds). The at_max  parameter is an upper-limit on the service time estimate, and is used as a 'failsafe' in case of rogue/bad/buggy code that would lead to never-ending estimate increases. If at_max is reached, an RPC request is considered 'broken' and should time out.

Setting at_max to 0 causes adaptive timeouts to be disabled and the old fixed-timeout method (obd_timeout) to be used. This is the default value in Lustre 1.6.5.

Note: It is possible that slow hardware might validly cause the service estimate to increase beyond the default value of at_max. In this case, you should increase at_max to the maximum time you are willing to wait for an RPC completion."""),
'sys.at_history': (FilesystemGlobalConfParam, IntegerParam(), "Sets a time period (in seconds) within which adaptive timeouts remember the slowest event that occurred. Default value is 600."),
'sys.at_early_margin': (FilesystemGlobalConfParam, IntegerParam(), "Sets how far before the deadline Lustre sends an early reply. Default value is 5."),
'sys.at_extra': (FilesystemGlobalConfParam, IntegerParam(), """Sets the incremental amount of time that a server asks for, with each early reply. The server does not know how much time the RPC will take, so it asks for a fixed value. Default value is 30. When a server finds a queued request about to time out (and needs to send an early reply out), the server adds the at_extra value. If the time expires, the Lustre client enters recovery status and reconnects to restore it to normal status.

If you see multiple early replies for the same RPC asking for multiple 30-second increases, change the at_extra value to a larger number to cut down on early replies sent and, therefore, network load."""),
# ldlm_enqueue_min does not appear to be conf_param'able
#'sys.ldlm_enqueue_min': (FilesystemGlobalConfParam, IntegerParam(), "Sets the minimum lock enqueue time. Default value is 100. The ldlm_enqueue  time is the maximum of the measured enqueue estimate (influenced by at_min and at_max parameters), multiplied by a weighting factor, and the ldlm_enqueue_min setting. LDLM lock enqueues were based on the obd_timeout  value; now they have a dedicated minimum value. Lock enqueues increase as the measured enqueue times increase (similar to adaptive timeouts)."),

# "Lustre Timeouts"
# =================
'sys.timeout': (FilesystemGlobalConfParam, IntegerParam(), "This is the time period that a client waits for a server to complete an RPC (default is 100s). Servers wait half of this time for a normal client RPC to complete and a quarter of this time for a single bulk request (read or write of up to 1 MB) to complete. The client pings recoverable targets (MDS and OSTs) at one quarter of the timeout, and the server waits one and a half times the timeout before evicting a client for being \"stale.\""),
'sys.ldlm_timeout': (FilesystemGlobalConfParam, IntegerParam(), "This is the time period for which a server will wait for a client to reply to an initial AST (lock cancellation request) where default is 20s for an OST and 6s for an MDS. If the client replies to the AST, the server will give it a normal timeout (half of the client timeout) to flush any dirty data and release the lock."),
}

# "Setting MDS and OSS Thread Counts"
# ===================================
for service in ['mdt.MDS.mds', 'mdt.MDS.mds_readpage', 'mdt.MDS.mds_setattr']:
    for param in ['thread_min', 'thread_max', 'thread_started']:
        all_params[service + "." + param] = (MdtConfParam, IntegerParam(), "")

for service in ['ost.OSS.ost', 'ost.OSS.ost_io', 'ost.OSS.ost_create']:
    for param in ['thread_min', 'thread_max', 'thread_started']:
        all_params[service + "." + param] = (OstConfParam, IntegerParam(), "")


_conf_param_klasses = [FilesystemClientConfParam, FilesystemGlobalConfParam, MdtConfParam, OstConfParam]
_possible_conf_params = {}

_conf_param_help = dict([(k, v[2]) for k, v in all_params.items()])


def get_conf_param_help(conf_param):
    return _conf_param_help[conf_param]


def get_possible_conf_params(klass):
    """A map of conf param name to documentation string"""
    from configure.models import ManagedOst, ManagedMdt, ManagedFilesystem

    conf_param_klasses = {
        ManagedOst: (OstConfParam,),
        ManagedMdt: (MdtConfParam,),
        ManagedFilesystem: (FilesystemClientConfParam, FilesystemGlobalConfParam)
    }[klass]
    try:
        return _possible_conf_params[conf_param_klasses]
    except KeyError:
        result = dict([(k, v[2]) for k, v in all_params.items() if v[0] in conf_param_klasses])
        _possible_conf_params[conf_param_klasses] = result
        return result


def get_conf_params(obj):
    from configure.models import ManagedOst, ManagedMdt, ManagedFilesystem, ConfParam

    if isinstance(obj, ManagedOst):
        conf_params_query = obj.ostconfparam_set.all()
    elif isinstance(obj, ManagedMdt):
        conf_params_query = obj.mdtconfparam_set.all()
    elif isinstance(obj, ManagedFilesystem):
        import itertools
        conf_params_query = itertools.chain(obj.filesystemclientconfparam_set.all(), obj.filesystemglobalconfparam_set.all())
    else:
        raise NotImplementedError()

    # First get explicitly set conf params
    set_conf_params = ConfParam.get_latest_params(conf_params_query)
    result = dict([(conf_param.key, conf_param.value) for conf_param in set_conf_params])
    # Then populate None for unset conf params
    for unset_conf_param in set(get_possible_conf_params(obj.__class__).keys()) ^ set(result.keys()):
        result[unset_conf_param] = None

    return result


def set_conf_param(obj, key, value):
    from configure.models import ManagedFilesystem, ManagedMdt, ManagedOst, FilesystemMember
    from configure.models import ApplyConfParams
    from configure.lib.state_manager import StateManager

    # TODO: check if the value is unchanged and return if so

    # TODO: provide a way for callers to wrap up multiple conf param set
    # operations into a Command for presentation

    if isinstance(obj, ManagedFilesystem):
        mgs = obj.mgs.downcast()
    elif isinstance(obj, FilesystemMember):
        mgs = obj.filesystem.mgs.downcast()
    else:
        raise NotImplementedError

    if isinstance(obj, ManagedFilesystem):
        kwargs = {'filesystem': obj}
    elif isinstance(obj, ManagedMdt):
        kwargs = {'mdt': obj}
    elif isinstance(obj, ManagedOst):
        kwargs = {'ost': obj}
    else:
        raise NotImplementedError

    model_klass, param_value_obj, help_text = all_params[key]
    p = model_klass(key = key,
                    value = value,
                    **kwargs)
    mgs.set_conf_params([p])
    StateManager().add_job(ApplyConfParams(mgs = mgs))
