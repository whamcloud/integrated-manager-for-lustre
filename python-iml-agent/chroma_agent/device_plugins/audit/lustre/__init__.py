# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import re
import heapq
from collections import defaultdict
from collections import namedtuple

from chroma_agent.device_plugins.audit import BaseAudit
from chroma_agent.device_plugins.audit.mixins import (
    FileSystemMixin,
    LustreGetParamMixin,
)


# HYD-2307 workaround
DISABLE_BRW_STATS = True
JOB_STATS_LIMIT = 20  # only return the most active jobs


def local_audit_classes():
    import chroma_agent.device_plugins.audit.lustre

    return [
        cls
        for cls in [
            getattr(chroma_agent.device_plugins.audit.lustre, name)
            for name in dir(chroma_agent.device_plugins.audit.lustre)
            if name.endswith("Audit")
        ]
        if hasattr(cls, "is_available") and cls.is_available()
    ]


class LustreAudit(BaseAudit, FileSystemMixin, LustreGetParamMixin):
    """Parent class for LustreAudit entities.

    Contains methods which are common to all Lustre cluster component types.
    """

    LustreVersion = namedtuple("LustreVersion", ["major", "minor", "patch"])

    @classmethod
    def is_available(cls):
        """Returns a boolean indicating whether or not this audit class should
        be instantiated.
        """
        return cls.kmod_is_loaded() and cls.device_is_present()

    @classmethod
    def device_is_present(cls):
        """Returns a boolean indicating whether or not this class
        has any corresponding Lustre device entries.
        """
        modname = cls.__name__.replace("Audit", "").lower()

        # There are some modules which can be loaded but don't have
        # corresponding device entries.  In these cases, just wink and
        # move on.
        exceptions = "lnet".split()
        if modname in exceptions:
            return True

        obj = cls()
        entries = [dev for dev in obj.devices() if dev["type"] == modname]
        return len(entries) > 0

    @classmethod
    def kmod_is_loaded(cls):
        """Returns a boolean indicating whether or not this class'
        corresponding Lustre module is loaded.
        """
        modname = cls.__name__.replace("Audit", "").lower()

        def filter(line):
            return line.startswith(modname)

        obj = cls()
        try:
            modules = list(obj.read_lines("/proc/modules", filter))
        except IOError:
            modules = []

        return len(modules) == 1

    def __init__(self, **kwargs):
        super(LustreAudit, self).__init__(**kwargs)

        self.raw_metrics["lustre"] = {}

    def stats_dict_from_path(self, path):
        """Creates a dict from Lustre stats file contents."""
        stats_re = re.compile(
            r"""
        # e.g.
        # create                    726 samples [reqs]
        # cache_miss                21108 samples [pages] 1 1 21108
        # obd_ping                  1108 samples [usec] 15 72 47014 2156132
        ^
        (?P<name>\w+)\s+(?P<count>\d+)\s+samples\s+\[(?P<units>\w+)\]
        (?P<min_max_sum>\s+(?P<min>\d+)\s+(?P<max>\d+)\s+(?P<sum>\d+)
        (?P<sumsq>\s+(?P<sumsquare>\d+))?)?
        $
        """,
            re.VERBOSE,
        )

        stats = {}

        # There is a potential race between the time that an OBD module
        # is loaded and the stats entry is created (HYD-389).  If we read
        # during that window, the audit will crash.  I'm not crazy about
        # excepting IOErrors as a general rule, but I suppose this is
        # the least-worst solution.
        try:
            for line in self.get_param_lines(path):
                match = re.match(stats_re, line)
                if not match:
                    continue

                name = match.group("name")
                stats[name] = {
                    "count": int(match.group("count")),
                    "units": match.group("units"),
                }
                if match.group("min_max_sum") is not None:
                    stats[name].update(
                        {
                            "min": int(match.group("min")),
                            "max": int(match.group("max")),
                            "sum": int(match.group("sum")),
                        }
                    )
                if match.group("sumsq") is not None:
                    stats[name].update({"sumsquare": int(match.group("sumsquare"))})
        except Exception:
            return stats

        return stats

    def dict_from_path(self, path):
        """Creates a dict from simple dict-like (k\s+v) file contents."""
        return dict(re.split("\s+", line) for line in self.get_param_lines(path))

    @property
    def version(self):
        """Returns a string representation of the local Lustre version."""
        try:
            return self.get_param_string("version")
        except Exception:
            return "0.0.0"

    @property
    def version_info(self):
        """Returns a LustreVersion containing major, minor and patch components of the local Lustre version."""
        result = []

        for element in (self.version.split(".") + ["0", "0", "0"])[0:3]:
            digits = re.match("\d+", element)

            if digits:
                result.append(int(digits.group()))
            else:
                result.append(0)

        return self.LustreVersion(*result)

    def health_check(self):
        """Returns a string containing Lustre's idea of its own health."""
        return self.get_param_string("health_check")

    def is_healthy(self):
        """Returns a boolean based on our determination of Lustre's health."""
        # NB: Currently we just rely on health_check, but there's no reason
        # we can't extend this to do more. (Perhaps subclass-specific checks?)
        return self.health_check() == "healthy"

    def devices(self):
        """Returns a list of Lustre devices local to this node."""
        try:
            return [
                dict(
                    zip(
                        ["index", "state", "type", "name", "uuid", "refcount"],
                        line.split(),
                    )
                )
                for line in self.get_param_lines("devices")
            ]
        except Exception:
            return []

    def _gather_raw_metrics(self):
        raise NotImplementedError

    def metrics(self):
        """Returns a hash of metric values."""
        self._gather_raw_metrics()
        return {"raw": self.raw_metrics}
