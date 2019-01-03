import os
import json
import collections
import operator

from chroma_core.lib.cache import ObjectCache
from chroma_core.lib import metrics
from chroma_core.models import ManagedTarget, ManagedTargetMount, ManagedMgs, ManagedMdt, ManagedOst, ManagedFilesystem
from chroma_core.models import Stats
from .chroma_api_test_case import ChromaApiTestCase
from tests.unit.chroma_core.helpers import synthetic_host, synthetic_volume_full


class TestStats(ChromaApiTestCase):
    def setUp(self):
        ChromaApiTestCase.setUp(self)
        fixture = collections.defaultdict(list)
        for line in open(os.path.join(os.path.dirname(__file__), "fixtures/stats.sjson")):
            data = json.loads(line.strip())
            fixture[data["type"], data["id"]].append((data["time"], data["data"]))
        # create gaps in data to test alignment
        for key in (min(fixture), max(fixture)):
            del fixture[key][-1]
        self.hosts = [synthetic_host("myserver{0:d}".format(n)) for n in range(2)]
        self.mgt, mounts = ManagedMgs.create_for_volume(synthetic_volume_full(self.hosts[0]).id, name="MGS")
        self.fs = ManagedFilesystem.objects.create(mgs=self.mgt, name="testfs")
        ObjectCache.add(ManagedFilesystem, self.fs)
        self.mdt, mounts = ManagedMdt.create_for_volume(synthetic_volume_full(self.hosts[0]).id, filesystem=self.fs)
        ObjectCache.add(ManagedTarget, self.mdt.managedtarget_ptr)
        for tm in mounts:
            ObjectCache.add(ManagedTargetMount, tm)

        self.osts = [
            ManagedOst.create_for_volume(synthetic_volume_full(self.hosts[1]).id, filesystem=self.fs)[0]
            for n in range(2)
        ]
        # store fixture data with corresponding targets
        for target, key in zip(self.hosts + [self.mdt] + self.osts, sorted(fixture)):
            store = metrics.MetricStore.new(target)
            kwargs = {"jobid_var": "procname_uid"} if isinstance(target, ManagedOst) else {}
            for timestamp, value in fixture[key]:
                Stats.insert(store.serialize(value, timestamp, **kwargs))
        for model in Stats:
            model.cache.clear()

    def fetch(self, path, **params):
        response = self.api_client.get("/api/" + path, data=params)
        self.assertHttpOK(response)
        return json.loads(response.content)

    def test(self):
        "Test various combinations of target or host, list or detail, latest or date range, reduce, and group."
        # target list, latest with reduce and group: verify staggered timestamps from both targets merge
        fs_id = str(self.fs.id)
        content = self.fetch(
            "target/metric/",
            metrics="kbytesfree,kbytestotal",
            latest="true",
            reduce_fn="average",
            kind="OST",
            group_by="filesystem",
        )
        self.assertEqual(list(content), [fs_id])
        data, timestamps = zip(*map(operator.itemgetter("data", "ts"), content[fs_id]))
        self.assertEqual(
            data,
            ({"kbytesfree": 1381963.5, "kbytestotal": 2015824.0}, {"kbytesfree": 1381963.5, "kbytestotal": 2015824.0}),
        )
        self.assertEqual(timestamps, ("2013-04-19T20:34:10+00:00", "2013-04-19T20:34:20+00:00"))

        # target list, latest with reduce and group: verify single reduced target
        content = self.fetch(
            "target/metric/",
            metrics="filesfree,filestotal",
            latest="true",
            reduce_fn="sum",
            kind="MDT",
            group_by="filesystem",
        )
        self.assertEqual(list(content), [fs_id])
        data, timestamps = zip(*map(operator.itemgetter("data", "ts"), content[fs_id]))
        self.assertEqual(data, ({"filesfree": 409026.0, "filestotal": 512000.0},))
        self.assertEqual(timestamps, ("2013-04-19T20:34:20+00:00",))

        # host list, date range with reduce: verify reduced hosts with one empty result
        content = self.fetch(
            "host/metric/",
            metrics="cpu_user,mem_MemFree",
            begin="2013-04-19T20:34:10Z",
            end="2013-04-19T20:34:30Z",
            reduce_fn="sum",
        )
        data, timestamps = zip(*map(operator.itemgetter("data", "ts"), content))
        self.assertEqual(data, ({"mem_MemFree": 68704.0, "cpu_user": 9.6},))
        self.assertEqual(timestamps, ("2013-04-19T20:34:20+00:00",))

        # host list, date range with reduce: verify single reduced host
        content = self.fetch(
            "host/metric/",
            metrics="cpu_user,mem_MemFree",
            begin="2013-04-19T20:33:50Z",
            end="2013-04-19T20:34:30Z",
            reduce_fn="sum",
            role="MDS",
        )
        data, timestamps = zip(*map(operator.itemgetter("data", "ts"), content))
        self.assertEqual(data, ({"cpu_user": 6.1, "mem_MemFree": 50110.0}, {"cpu_user": 9.6, "mem_MemFree": 47246.0}))
        self.assertEqual(timestamps, ("2013-04-19T20:34:00+00:00", "2013-04-19T20:34:10+00:00"))

        # host list, date range: verify separate single host
        host_id = str(self.hosts[1].id)
        content = self.fetch(
            "host/metric/",
            metrics="cpu_user,mem_MemFree",
            begin="2013-04-19T20:34:00Z",
            end="2013-04-19T20:34:30Z",
            role="OSS",
        )
        self.assertEqual(list(content), [host_id])
        data, timestamps = zip(*map(operator.itemgetter("data", "ts"), content[host_id]))
        self.assertEqual(data, ({"mem_MemFree": 65001.0, "cpu_user": 5.9}, {"mem_MemFree": 68704.0, "cpu_user": 9.6}))
        self.assertEqual(timestamps, ("2013-04-19T20:34:10+00:00", "2013-04-19T20:34:20+00:00"))

        # target detail, date range: verify basic target retrieval
        content = self.fetch(
            "target/{0}/metric/".format(self.mdt.id),
            metrics="stats_close,stats_mkdir",
            begin="2013-04-19T20:34:00Z",
            end="2013-04-19T20:34:30Z",
        )
        data, timestamps = zip(*map(operator.itemgetter("data", "ts"), content))
        self.assertEqual(
            data, ({"stats_close": 906.5, "stats_mkdir": 610.6}, {"stats_close": 389.7, "stats_mkdir": 862.5})
        )
        self.assertEqual(timestamps, ("2013-04-19T20:34:10+00:00", "2013-04-19T20:34:20+00:00"))

        # target detail, latest: verify target retrieval with missing field
        content = self.fetch(
            "target/{0}/metric/".format(self.osts[0].id), metrics="kbytesfree,filestotal,missing", latest="true"
        )
        data, timestamps = zip(*map(operator.itemgetter("data", "ts"), content))
        self.assertEqual(data, ({"filestotal": 128000.0, "kbytesfree": 1418841.0, "missing": 0.0},))
        self.assertEqual(timestamps, ("2013-04-19T20:34:20+00:00",))

        # target detail, date range: verify target retrieval with missing timestamp
        content = self.fetch(
            "target/{0}/metric/".format(self.osts[1].id),
            max_points="100",
            metrics="stats_read_bytes,stats_write_bytes",
            begin="2013-04-19T20:34:00Z",
            end="2013-04-19T20:34:30Z",
        )
        data, timestamps = zip(*map(operator.itemgetter("data", "ts"), content))
        self.assertEqual(data, ({"stats_write_bytes": 1517052856.4, "stats_read_bytes": 259273421.2},))
        self.assertEqual(timestamps, ("2013-04-19T20:34:10+00:00",))

        # target detail and list, with job stats
        for name in ("read_bytes", "write_bytes", "read_iops", "write_iops", "metadata_iops"):
            content, = self.fetch(
                "target/{0}/metric/".format(self.osts[0].id),
                job="id",
                metrics=name,
                begin="2013-04-19T20:30:00Z",
                end="2013-04-19T20:34:30Z",
            )
            self.assertEqual(content["ts"], "2013-04-19T20:34:20+00:00")
            self.assertEqual(content["data"], {"cp.0": 0.0, "dd.0": 0.0})
            for job, keys in [("user", ["0"]), ("name", ["cp", "dd"]), ("missing", ["cp.0", "dd.0"])]:
                content = self.fetch(
                    "target/metric/",
                    job=job,
                    metrics=name,
                    begin="2013-04-19T20:30:00Z",
                    end="2013-04-19T20:34:30Z",
                    kind="OST",
                )
                self.assertEqual(content[str(self.osts[1].id)], [])
                item, = content[str(self.osts[0].id)]
                self.assertEqual(item["data"], dict.fromkeys(keys, 0.0))

        # fixed number of points
        content = self.fetch(
            "host/metric/",
            num_points=2,
            metrics="mem_MemTotal,mem_MemFree",
            begin="2013-04-19T20:33:00Z",
            end="2013-04-19T20:34:00Z",
            role="OSS",
        )
        data, = content.values()
        self.assertEqual(
            map(operator.itemgetter("ts"), data), ["2013-04-19T20:33:00+00:00", "2013-04-19T20:33:30+00:00"]
        )

        # invalid requests
        response = self.api_client.get(
            "/api/target/metric/",
            data={"num_points": "", "job": "id", "latest": "true", "metrics": "read_bytes,write_bytes"},
        )
        self.assertHttpBadRequest(response)
        content = json.loads(response.content)
        self.assertEqual(len(content["job"]), 2)
        self.assertEqual(len(content["num_points"]), 2)
        response = self.api_client.get("/api/target/metric/", data={"job": "id", "begin": "2013-04-19T20:33:00Z"})
        self.assertHttpBadRequest(response)

        # discover available metrics
        content, = self.fetch("target/{0}/metric/".format(self.osts[0].id), latest="true")
        prefixes = set(name.split("_")[0] for name in content["data"])
        for total, count in [("stats_read_bytes", "stats_read_iops"), ("stats_write_bytes", "stats_write_iops")]:
            self.assertGreater(content["data"][total], content["data"][count])
        self.assertIn("stats", prefixes)
        self.assertNotIn("job", prefixes)
        content = self.fetch("host/metric/", latest="true")
        for (data,) in content.values():
            prefixes = set(name.split("_")[0] for name in data["data"])
            self.assertEqual(prefixes, set(["mem", "cpu"]))
